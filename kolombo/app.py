from __future__ import annotations

import os.path
import re
import sys
import traceback
from argparse import SUPPRESS, Action, ArgumentParser, HelpFormatter
from typing import Optional, List, Iterable

from pytermor import fmt
from pytermor.fmt import Format

from .formatter.binary import BinaryFormatter
from .formatter.text import TextFormatter
from .reader.binary import BinaryReader
from .reader.text import TextReader
from .settings import Settings
from .writer import Writer


class CustomHelpFormatter(HelpFormatter):
    INDENT_INCREMENT = 2
    INDENT = ' ' * INDENT_INCREMENT

    @staticmethod
    def format_header(title: str) -> str:
        return fmt.bold(title.upper())

    def __init__(self, prog):
        super().__init__(prog, max_help_position=30, indent_increment=self.INDENT_INCREMENT)

    def start_section(self, heading: Optional[str]) -> None:
        super().start_section(self.format_header(heading))

    def add_usage(self, usage: Optional[str], actions: Iterable[Action], groups: Iterable,
                  prefix: Optional[str] = ...) -> None:
        super().add_text(self.format_header('usage: '))
        super().add_usage(usage, actions, groups, prefix=self.INDENT)

    def add_examples(self, examples: List[str]):
        self.start_section('example' + ('s' if len(examples) > 1 else ''))
        self._add_item(self._format_text, ['\n'.join(examples)])
        self.end_section()

    def _format_action_invocation(self, action):
        # same as in superclass, but without printing argument for short options
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            parts = []
            if action.nargs == 0:
                parts.extend(action.option_strings)
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    if len(option_string) > 2 or len(action.option_strings) == 1:
                        parts.append(f'{option_string} {args_string}')
                    else:
                        parts.append(option_string)

            return ', '.join(parts)

    def _format_text(self, text: str) -> str:
        return super()._format_text(text).rstrip('\n') + '\n'

    def _fill_text(self, text, width, indent):
        return ''.join(indent + line for line in text.splitlines(keepends=True))


class CustomArgumentParser(ArgumentParser):
    def __init__(self, examples: List[str] = None, epilog: List[str] = None, **kwargs):
        self.examples = examples
        kwargs.update({'epilog': '\n'.join(epilog)})
        super(CustomArgumentParser, self).__init__(**kwargs)

    def format_help(self) -> str:
        formatter = self._get_formatter()
        if self.epilog:
            formatter.add_text(' ')
            formatter.add_text(self.epilog)
        if self.examples and isinstance(formatter, CustomHelpFormatter):
            formatter.add_examples(self.examples)

        ending_formatted = formatter.format_help()
        self.epilog = None

        result = super().format_help() + ending_formatted
        result = re.sub(r'(\033\[[0-9;]*m)?\s*:\s*(\n|\033|$)', r'\1\2', result)
        return result


# noinspection PyMethodMayBeStatic
class App:
    BINARY_MODE: bool

    def run(self):
        _hanlder = ExceptionHandler()
        try:
            self._invoke()
        except Exception as e:
            _hanlder.handle(e)
        print()

    def _invoke(self):
        self._parse_args()
        if Settings.legend:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'legend.ansi'), 'rt') as f:
                print(f.read())
                exit(0)
        App.BINARY_MODE = Settings.binary

        writer = Writer()
        if self.BINARY_MODE:
            reader = BinaryReader(Settings.filename, BinaryFormatter(writer))
        else:
            reader = TextReader(Settings.filename, TextFormatter(writer))

        try:
            reader.read()
        except UnicodeDecodeError:
            if not self.BINARY_MODE:
                print('Binary data detected, cannot proceed in text mode')
                print('Use -b option to run in binary mode')
            else:
                raise

    def _parse_args(self):
        parser = CustomArgumentParser(
            description='Escape sequences and control characters visualiser',
            usage='%(prog)s [-t | -b | -l | -h] [<options>] [<file>]',
            epilog=[
                'Mandatory or optional arguments to long options are also mandatory or optional for any'
                ' corresponding short options.',
                '',
                'Ignore-<class> options are interpreted as follows::',
                f'{CustomHelpFormatter.INDENT}* In text mode: replace printable characters to "×", hide markers'
                f' of non-printable characters;',
                f'{CustomHelpFormatter.INDENT}* In binary mode: replace ignored chars to "×" and color their hex codes dark gray.',
                '',
                '(c) 2022 A. Shavykin <0.delameter@gmail.com>',
            ],
            examples=[
                '%(prog)s -i 2 -e --ignore-space file.txt',
                '%(prog)s -b -w16 file.bin', '\n'
            ],
            add_help=False,
            formatter_class=lambda prog: CustomHelpFormatter(prog),
        )
        parser.add_argument('filename', metavar='<file>', nargs='?',
                            help='file to read from; if empty or "-", read stdin instead')

        modes_group = parser.add_argument_group('mode selection')
        modes_group_nested = modes_group.add_mutually_exclusive_group()
        modes_group_nested.add_argument('-t', '--text', action='store_true', default=True,
                                        help='open file in text mode (this is the default)')
        modes_group_nested.add_argument('-b', '--binary', action='store_true', default=False,
                                        help='open file in binary mode')
        modes_group_nested.add_argument('-l', '--legend', action='store_true', default=False,
                                        help='show annotation symbol list and exit')
        modes_group.add_argument('-h', '--help', action='help', default=SUPPRESS,
                                 help='show this help message and exit')

        generic_group = parser.add_argument_group('generic options')
        esc_output_group = generic_group.add_mutually_exclusive_group()
        space_output_group = generic_group.add_mutually_exclusive_group()
        control_output_group = generic_group.add_mutually_exclusive_group()
        esc_output_group.add_argument('-e', '--focus-esc', action='store_true', default=False,
                                      help='highlight escape sequences markers')
        space_output_group.add_argument('-s', '--focus-space', action='store_true', default=False,
                                        help='highlight whitespace markers')
        control_output_group.add_argument('-c', '--focus-control', action='store_true', default=False,
                                          help='highlight control char markers')
        esc_output_group.add_argument('-E', '--ignore-esc', action='store_true', default=False,
                                      help='ignore escape sequences')
        space_output_group.add_argument('-S', '--ignore-space', action='store_true', default=False,
                                        help='ignore whitespaces')
        control_output_group.add_argument('-C', '--ignore-control', action='store_true', default=False,
                                          help='ignore control chars')
        generic_group.add_argument('--no-color-content', action='store_true', default=False,
                                   help='disable applying input file formatting to the output')

        text_mode_group = parser.add_argument_group('text mode only')
        text_mode_group.add_argument('-i', '--info', metavar='<level>', action='store', type=int, default=1,
                                     help='control and escape marker details (0-2, default %(default)s)')
        text_mode_group.add_argument('-L', '--max-lines', metavar='<num>', action='store', type=int, default=0,
                                     help='stop after reading <num> lines')
        text_mode_group.add_argument('--no-line-numbers', action='store_true', default=False,
                                     help='do not print line numbers')
        text_mode_group.add_argument('--no-color-markers', action='store_true', default=False,
                                     help='disable applying input file formatting to SGR markers')
        text_mode_group.add_argument('--pipe-stderr', action='store_true', default=False,
                                     help='send raw input lines to stderr along with default output')

        bin_mode_group = parser.add_argument_group('binary mode only')
        utf8_output_group = bin_mode_group.add_mutually_exclusive_group()
        utf8_output_group.add_argument('-u', '--focus-utf8', action='store_true', default=False,
                                       help='highlight utf-8 sequences')
        utf8_output_group.add_argument('-U', '--ignore-utf8', action='store_true', default=False,
                                       help='ignore utf-8 sequences')
        bin_mode_group.add_argument('-d', '--decode', action='store_true', default=False,
                                    help='decode valid utf-8 sequences, print as unicode chars (in right panel)')
        bin_mode_group.add_argument('-B', '--max-bytes', metavar='<num>', action='store', type=int, default=0,
                                    help='stop after reading <num> bytes')
        bin_mode_group.add_argument('-w', '--columns', metavar='<num>', action='store', type=int, default=0,
                                    help='format output as <num>-columns wide table (default %(default)s = auto)')
        bin_mode_group.add_argument('-g', '--grid', action='store_true', default=False,
                                    help='overlay byte table with 8x8')

        return parser.parse_args(namespace=Settings)


class ExceptionHandler:
    def __init__(self):
        self.format: Format = fmt.red

    def handle(self, e: Exception):
        self._log_traceback(e)
        print()
        exit(1)

    def _write(self, s: str):
        print(self.format(s), file=sys.stderr)

    def _log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n')
                    for line
                    in traceback.format_exception(e.__class__, e, ex_traceback)]
        self._write("\n".join(tb_lines))
