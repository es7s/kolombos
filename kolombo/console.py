from __future__ import annotations

import sys
import traceback
from abc import ABCMeta, abstractmethod
from math import ceil
from typing import List

from pytermor import autof, seq, fmt
from pytermor.fmt import AbstractFormat
from pytermor.util import ReplaceSGR

from .error import ArgumentError
from .settings import SettingsManager
from .util import get_terminal_width


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
            prefix = Console.format_prefix(line_num, fmt_)
        elif SettingsManager.app_settings.no_line_numbers:
            prefix = ''
        else:
            prefix = fmt_(f'{line_num:2d}') + Console.get_separator()

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def write_with_offset(self, s: str, offset: int, end='\n', flush=True):
        fmt_ = fmt.green
        prefix = Console.format_prefix_with_offset(offset, fmt_)

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
    def format_prefix(label: str, f: AbstractFormat) -> str:
        return f(f'{label!s:>{Console.MAIN_PREFIX_LEN}.{Console.MAIN_PREFIX_LEN}s}') + Console.get_separator()

    @staticmethod
    def format_prefix_with_offset(offset: int, f: AbstractFormat = fmt.green) -> str:
        if SettingsManager.app_settings.decimal_offsets:
            offset_str = f'{offset:d}'
        else:
            offset_str = f'0x{offset:0{ceil(len(str(offset))/2)*2}x}'
        return Console.format_prefix(offset_str, f)

    @staticmethod
    def print(s: str, end='\n', **kwargs):
        print(s, end=end, **kwargs)

    @staticmethod
    def _format_separator(s: str) -> str:
        return autof(seq.GRAY)(s) if SettingsManager.app_settings.debug > 0 else fmt.cyan(s)
