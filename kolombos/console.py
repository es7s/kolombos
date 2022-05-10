# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

import re
import sys
import traceback
from abc import ABCMeta, abstractmethod
from math import ceil
from typing import List, Any

from pytermor import autof, seq, fmt, SequenceSGR, ReplaceSGR, Format

from . import ArgumentError, get_terminal_width
from .byteio import CharClass
from .settings import SettingsManager, Settings


# noinspection PyMethodMayBeStatic
class AbstractConsoleBuffer(metaclass=ABCMeta):
    @abstractmethod
    def flush(self): raise NotImplementedError


class ConsoleOutputBuffer(AbstractConsoleBuffer):
    def __init__(self):
        self._buf = ''
        Console.register_buffer(self)

    def write(self, s: str, end='\n', flush=True):
        self._buf += f'{s}{end}'
        if flush:
            self.flush()

    def write_with_line_num(self, s: str, line_num: int, end='', flush=True):
        fmt_ = fmt.green
        if SettingsManager.app_settings.debug:
            prefix = Console.format_prefix(str(line_num), fmt_)
        elif SettingsManager.app_settings.no_line_numbers:
            prefix = ''
        else:
            prefix = fmt_(f'{line_num:2d}') + Console.get_separator()

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def write_with_offset(self, s: str, offset: int, end='\n', flush=True):
        fmt_ = fmt.green
        if SettingsManager.app_settings.effective_print_offsets:
            prefix = Console.format_prefix_with_offset(offset, fmt_)
        else:
            prefix = ''

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def flush(self):
        if not self._buf:
            return

        Console.print(self._buf, end='')
        self._buf = ''


class ConsoleDebugBuffer(AbstractConsoleBuffer):
    def __init__(self, key_prefix: str = None, prefix_offset_color: SequenceSGR = seq.GRAY):
        self._buf = ''

        self._default_prefix = Console.format_prefix(key_prefix, autof(seq.GRAY + seq.BG_BLACK)) if key_prefix else None
        self._prefix_fmt = autof(prefix_offset_color + seq.BG_BLACK)

        Console.register_buffer(self)

    def write(self, level: int, s: str, offset: int = None, end='\n', no_default_prefix=False, flush=True):
        if SettingsManager.app_settings.debug < level:
            return

        prefix = ''
        if isinstance(offset, int):
            prefix = Console.format_prefix_with_offset(offset, self._prefix_fmt)
        elif self._default_prefix is not None:
            if not no_default_prefix:
                prefix = self._default_prefix

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def flush(self):
        if not self._buf:
            return

        Console.debug(self._buf, end='')
        self._buf = ''


class Console:
    FMT_WARNING = autof(seq.HI_YELLOW)
    FMT_ERROR_TRACE = fmt.red
    FMT_ERROR = autof(seq.HI_RED)
    MAIN_PREFIX_LEN = 8

    buffers: List[AbstractConsoleBuffer] = list()
    settings_prefix_len: int = 0

    @staticmethod
    def register_buffer(buffer: AbstractConsoleBuffer):
        Console.buffers.append(buffer)

    @staticmethod
    def flush_buffers():
        for buffer in Console.buffers:
            buffer.flush()

    @staticmethod
    def on_exception(e: Exception):
        Console.flush_buffers()

        if isinstance(e, ArgumentError):
            Console.error(f'{e.__class__.__name__}: {e!s}')
            Console.info(e.USAGE_MSG)

        elif SettingsManager.app_settings.debug > 0:
            tb_lines = [line.rstrip('\n')
                        for line
                        in traceback.format_exception(e.__class__, e, e.__traceback__)]
            error = tb_lines.pop(-1)
            Console.print(Console.FMT_ERROR_TRACE('\n'.join(tb_lines)))
            Console.error(error)

        else:
            Console.error(f'{e.__class__.__name__}: {e!s}')
            Console.info("Run the app with '"+fmt.bold('--debug')+"' argument to see the details")

    @staticmethod
    def debug(s: str = '', end='\n'):
        Console.print(s, end=end)

    @staticmethod
    def info(s: str = '', end='\n'):
        Console.print(s, end=end)

    @staticmethod
    def warn(s: str = '', end='\n'):
        Console.print(Console.FMT_WARNING(f'WARNING: {s}'), end=end)

    @staticmethod
    def error(s: str = '', end='\n'):
        Console.print(Console.FMT_ERROR(fmt.bold('ERROR: ') + s), end=end, file=sys.stderr)

    @staticmethod
    def get_separator() -> str:
        return Console._format_separator('│')

    @staticmethod
    def get_separator_line(
        settings_open: bool = False,
        settings_mid: bool = False,
        settings_close: bool = False,
        main_open: bool = False,
        main_close: bool = False,
    ) -> str:
        settings_cross = '─'
        main_cross = '┼'
        if settings_open:
            settings_cross = '┬'
            main_cross = '─'
        if settings_mid:
            settings_cross = '┼'
            main_cross = '─'
        if settings_close:
            settings_cross = '┴'
        if main_open:
            main_cross = '┬'
        if main_close:
            main_cross = '┴'

        main_raw = '─' * Console.MAIN_PREFIX_LEN
        settings_part = ''
        if Console.settings_prefix_len and (settings_open or settings_mid or settings_close):
            main_part = autof(seq.BG_BLACK)(main_raw + main_cross)
            settings_part = (autof(seq.BG_BLACK)('─' * (Console.settings_prefix_len - Console.MAIN_PREFIX_LEN - 1)) +
                             settings_cross)
        else:
            main_part = autof(seq.BG_BLACK)(main_raw) + main_cross

        max_width = get_terminal_width(exact=True)
        filler_len = max_width - len(ReplaceSGR('').apply(main_part+settings_part))

        return Console._format_separator(main_part + settings_part + ('─' * filler_len))

    @staticmethod
    def debug_settings():
        app_settings = SettingsManager.app_settings
        if not app_settings.debug_settings:
            return

        def is_derived(attr: str, settings: Settings) -> bool:
            return attr not in settings.__dict__

        def debug_print(attr, app_value, default_value):
            if app_value != default_value:
                fmt_attr_seq = fmt_header.opening_seq
                values = fmt.green(f'{app_value!s}') + ' ' + fmt.gray(f'[{default_value!s}]')
            else:
                fmt_attr_seq = seq.BG_BLACK
                values = fmt.yellow(f'{default_value!s}')

            if is_derived(attr, app_settings):
                fmt_attr_seq += seq.ITALIC

            debug_buffer.write(3, autof(fmt_attr_seq)(attr.rjust(max_attr_len)) + Console.get_separator() + values)

        default_settings = Settings()
        debug_buffer = ConsoleDebugBuffer()
        fmt_header = autof(seq.BG_BLACK + seq.BOLD)
        derived = app_settings.debug_settings_derived

        attrs = [attr for attr in sorted(
            app_settings.__dir__(),
            key=lambda attr: attr if is_derived(attr, app_settings) else '_'+attr
        ) if not attr.startswith(('_', 'init', 'get')) and (not is_derived(attr, app_settings) or derived)]

        max_attr_len = max([len(attr) for attr in attrs]) + 3
        Console.settings_prefix_len = max_attr_len

        debug_buffer.write(3, Console.get_separator_line(settings_open=True))
        header = 'Settings [Derived]'.upper().ljust(max_attr_len)
        if derived:
            header = header.replace('[', f'[{seq.ITALIC}').replace(']', f'{seq.ITALIC_OFF}]')
        else:
            header = re.sub(r'\[\w+]', lambda m: len(m.group(0)) * ' ', header)

        debug_buffer.write(3, fmt_header(header) + Console.get_separator())

        for attr in attrs:
            debug_print(attr, getattr(app_settings, attr), getattr(default_settings, attr))

        if derived:
            for char_class in CharClass:
                debug_print(f'{char_class}',
                            app_settings.get_char_class_display_mode(char_class),
                            default_settings.get_char_class_display_mode(char_class))

        debug_buffer.write(3, Console.get_separator_line(settings_close=True, main_open=True))

    @staticmethod
    def format_prefix(label: str, f: Format) -> str:
        return f(f'{label!s:>{Console.MAIN_PREFIX_LEN}.{Console.MAIN_PREFIX_LEN}s}') + Console.get_separator()

    @staticmethod
    def format_prefix_with_offset(offset: int, f: Format = fmt.green) -> str:
        if SettingsManager.app_settings.decimal_offsets:
            offset_str = f'{offset:d}'
        else:
            offset_str = f'0x{offset:0{ceil(len(str(offset))/2)*2}x}'
        return Console.format_prefix(offset_str, f)

    @staticmethod
    def print(s: str, end='\n', **kwargs):
        print(s, end=end, **kwargs)

    @staticmethod
    def printd(v: Any, max_input_len: int = 5) -> str:
        if SettingsManager.app_settings.debug_buffer_contents_full:
            max_input_len = sys.maxsize

        if hasattr(v, 'preview'):
            v = v.preview(max_input_len)

        if isinstance(v, (bytes, List)):
            result = 'len ' + fmt.bold(len(v))
            if not SettingsManager.app_settings.debug_buffer_contents:
                return result

            if len(v) == 0:
                return f'{result} {seq.GRAY}[]{seq.COLOR_OFF}'
            if isinstance(v, bytes):
                v = ' '.join([f'{b:02x}' for b in v])
            return f'{result} ' + \
                   f'{seq.GRAY}[' + \
                   f'{v[:2*(max_input_len-1)]}' + \
                   ('.. ' + ''.join(v[-2:])if len(v) > 2 * (max_input_len - 1) else '') + \
                   f']{seq.COLOR_OFF}'

        return f'{v!s}'

    @staticmethod
    def _format_separator(s: str) -> str:
        return autof(seq.GRAY)(s) if SettingsManager.app_settings.debug > 0 else fmt.cyan(s)
