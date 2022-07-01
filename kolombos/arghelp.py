# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
import re
from argparse import HelpFormatter, Action, ArgumentParser, SUPPRESS
from typing import Optional, Iterable, List

from pytermor import fmt

from .byteio import Reader
from .byteio.template import Template


class CustomHelpFormatter(HelpFormatter):
    INDENT_INCREMENT = 2
    INDENT = ' ' * INDENT_INCREMENT

    @staticmethod
    def format_header(title: str) -> str:
        return fmt.bold(title.upper())

    def __init__(self, prog):
        super().__init__(prog, max_help_position=30, indent_increment=self.INDENT_INCREMENT)

    def start_section(self, heading: Optional[str]):
        super().start_section(self.format_header(heading))

    def add_usage(self, usage: Optional[str], actions: Iterable[Action], groups: Iterable,
                  prefix: Optional[str] = ...):
        super().add_text(self.format_header('usage'))

        usage = usage.replace("\n", f"\n{self.INDENT}")
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
    def __init__(self, examples: List[str] = None, epilog: List[str] = None, usage: List[str] = None, **kwargs):
        self.examples = examples
        kwargs.update({
            'epilog': '\n'.join(epilog),
            'usage': '\n'.join(usage),
        })
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
        # remove ':' from headers ('<_b>header:<_f>'):
        result = re.sub(r'(\033\[[0-9;]*m)?\s*:\s*(\n|\033|$)', r'\1\2', result)
        return result


class AppArgumentParser(CustomArgumentParser):
    def __init__(self):
        fmt_b = fmt.bold
        fmt_u = fmt.underlined
        fmt_default = fmt.yellow

        super().__init__(
            description='Escape sequences and control characters visualiser',
            usage=[
                '%(prog)s [[--text] | --binary] [<options>] [<file>]',
                '%(prog)s --legend',
                '%(prog)s --version',
                '%(prog)s --help',
            ],
            epilog=[
                'Mandatory or optional arguments to long options are also mandatory or optional for any'
                ' corresponding short options. Arguments can be separated with both space or "=" in both cases.',
                '',
                f'Binary mode disables {fmt_b("--marker")} setting, because marker length should be always equal to actual sequence length. Therefore, control chars have 0 details level, while escape seqs are displayed with full details (2). Also, debug mode sets {fmt_b("--buffer")} setting to {Reader.READ_CHUNK_SIZE_DEBUG} bytes (however, it can be overriden as usual).',
                '',
                '(c) 2022 A. Shavykin <0.delameter@gmail.com>',
            ],
            examples=[
                'Read file in text mode, highlight escape sequences, marker verbosity 2 (max)',
                ''.ljust(4) + f"{fmt_u('%(prog)s')} --focus-esc -m{fmt_u(2)} file.txt",
                '',
                'Read file in binary mode, ignore whitespace, printables and UTF-8 sequences',
                ''.ljust(4) + f"{fmt_u('%(prog)s')} --binary -USP file.bin",
                '',
                'Read stdin in binary mode, highlight control characters, process 128 first bytes and exit',
                ''.ljust(4) + f"{fmt_u('%(prog)s')} --binary --focus-control -B{fmt_u(128)}",
                '',
                'Display annotation symbol list and color map',
                ''.ljust(4) + f"{fmt_u('%(prog)s')} --legend",
                '\n'
            ],
            add_help=False,
            formatter_class=lambda prog: CustomHelpFormatter(prog),
            prog='kolombos'
        )

        self.add_argument('filename', metavar='<file>', nargs='?', help='file to read from; if empty or "-", read stdin instead')

        modes_group = self.add_argument_group('operating mode')
        modes_group_nested = modes_group.add_mutually_exclusive_group()
        # modes_group_nested.add_argument('-a', '--auto', action='store_true', default=True, help='open file in text mode, fallback to binary on failure (default)')
        modes_group_nested.add_argument('-t', '--text', action='store_true', default=True, help='open file in text mode '+fmt_default('[this is a default]'))
        modes_group_nested.add_argument('-b', '--binary', action='store_true', default=False, help='open file in binary mode')
        modes_group_nested.add_argument('-l', '--legend', action='store_true', default=False, help='show annotation symbol list and exit')
        modes_group.add_argument('-v', '--version', action='store_true', default=False, help='show app version and exit')
        modes_group.add_argument('-h', '--help', action='help', default=SUPPRESS, help='show this help message and exit')

        char_class_group = self.add_argument_group('character class options')
        space_output_group = char_class_group.add_mutually_exclusive_group()
        control_output_group = char_class_group.add_mutually_exclusive_group()
        printable_output_group = char_class_group.add_mutually_exclusive_group()
        esc_output_group = char_class_group.add_mutually_exclusive_group()
        utf8_output_group = char_class_group.add_mutually_exclusive_group()
        binary_output_group = char_class_group.add_mutually_exclusive_group()
        space_output_group.add_argument('-s', '--focus-space', action='store_true', default=False, help='highlight whitespace markers')
        control_output_group.add_argument('-c', '--focus-control', action='store_true', default=False, help='highlight control char markers')
        printable_output_group.add_argument('-p', '--focus-printable', action='store_true', default=False, help='highlight printable chars')
        esc_output_group.add_argument('-e', '--focus-esc', action='store_true', default=False, help='highlight escape sequences markers')
        utf8_output_group.add_argument('-u', '--focus-utf8', action='store_true', default=False, help='highlight UTF-8 sequences')
        binary_output_group.add_argument('-i', '--focus-binary', action='store_true', default=False, help='highlight binary data bytes')
        space_output_group.add_argument('-S', '--ignore-space', action='store_true', default=False, help='dim/hide whitespaces')
        control_output_group.add_argument('-C', '--ignore-control', action='store_true', default=False, help='dim/hide control chars')
        printable_output_group.add_argument('-P', '--ignore-printable', action='store_true', default=False, help='dim/hide printable chars')
        esc_output_group.add_argument('-E', '--ignore-esc', action='store_true', default=False, help='dim/hide escape sequences')
        utf8_output_group.add_argument('-U', '--ignore-utf8', action='store_true', default=False, help='dim/hide UTF-8 sequences')
        binary_output_group.add_argument('-I', '--ignore-binary', action='store_true', default=False, help='dim/hide binary data')

        generic_group = self.add_argument_group('generic options')
        generic_group.add_argument('-L', '--max-lines', metavar='<num>', action='store', type=int, default=0, help='stop after reading <num> lines '+fmt_default('[default: no limit]'))
        generic_group.add_argument('-B', '--max-bytes', metavar='<num>', action='store', type=int, default=0, help='stop after reading <num> bytes '+fmt_default('[default: no limit]'))
        generic_group.add_argument('-f', '--buffer', metavar='<size>', type=int, default=None, help='read buffer size, in bytes '+fmt_default(f'[default: {Reader.READ_CHUNK_SIZE}]'))
        generic_group.add_argument('-d', '--debug', action='count', default=0, help='enable debug mode; can be used from 1 to 4 times, each level increases verbosity (-d|dd|ddd|dddd)')
        generic_group.add_argument('--no-color-markers', action='store_true', default=False, help='disable applying self-formatting to SGR marker details')

        text_mode_group = self.add_argument_group('text mode options')
        text_mode_group.add_argument('-m', '--marker', metavar='<details>', action='store', type=int, default=1, help='marker details: 0 is none, 1 is brief, 2 is full '+fmt_default('[default: %(default)s]'))
        text_mode_group.add_argument('--no-separators', action='store_true', default=False, help='do not print '+Template.wrap_in_separators('separators')+' around escape sequences')
        # text_mode_group.add_argument('-Q', '--squash-ignored', action='store_true', default=False, help=autof(seq.HI_YELLOW)('TODO ')+'replace sequences of ignored characters with one character')
        # text_mode_group.add_argument('-H', '--hide-ignored', action='store_true', default=False, help=autof(seq.HI_YELLOW)('TODO ')+'completely hide ignored character classes')
        text_mode_group.add_argument('--no-line-numbers', action='store_true', default=False, help='do not print line numbers')

        bin_mode_group = self.add_argument_group('binary mode options')
        bin_mode_group.add_argument('-w', '--columns', metavar='<num>', action='store', type=int, default=0, help='format output as <num>-columns wide table '+fmt_default('[default: auto]'))
        bin_mode_group.add_argument('-D', '--decode', action='store_true', default=False, help='decode valid UTF-8 sequences, print as unicode chars')
        offsets_group = bin_mode_group.add_mutually_exclusive_group()
        offsets_group.add_argument('--decimal-offsets', action='store_true', default=False, help='output offsets in decimal format '+fmt_default('[default: hex format]'))
        offsets_group.add_argument('--no-offsets', action='store_true', default=False, help='do not print offsets')
