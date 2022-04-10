from __future__ import annotations

import sys
import traceback
from abc import ABCMeta, abstractmethod
from math import ceil
from typing import List

from pytermor import autof, seq, fmt
from pytermor.fmt import AbstractFormat

from .error import ArgumentError
from .settings import Settings
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
        if Settings.debug:
            prefix = Console.format_prefix(str(line_num), fmt.green)
        elif Settings.no_line_numbers:
            prefix = ''
        else:
            prefix = fmt.green(f'{line_num:2d}') + Console.get_separator()

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def write_with_offset(self, s: str, offset: int, end='\n', flush=True):
        prefix = Console.format_prefix_with_offset(offset, fmt.green)

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def flush(self):
        if not self._buf:
            return

        Console.print(self._buf, end='')
        self._buf = ''


class ConsoleDebugBuffer(AbstractConsoleBuffer):
    def __init__(self, key_prefix: str = None, prefix_fmt: AbstractFormat = fmt.green):
        self._buf = ''

        self._default_prefix = Console.format_prefix(key_prefix, fmt.gray) if key_prefix else None
        self._prefix_fmt = prefix_fmt

        Console.register_buffer(self)

    def write(self, level: int, s: str, offset: int = None, end='\n', no_default_prefix=False, flush=True):
        if Settings.debug < level:
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

    buffers: List[AbstractConsoleBuffer] = list()

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

        elif Settings.debug > 0:
            tb_lines = [line.rstrip('\n')
                        for line
                        in traceback.format_exception(e.__class__, e, e.__traceback__)]
            error = tb_lines.pop(-1)
            Console.print(Console.FMT_ERROR_TRACE('\n'.join(tb_lines)))
            Console.error(error)

        else:
            Console.error(f'{e.__class__.__name__}: {e!s}')
            Console.info("Run the app with '--debug' argument to see the details")

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
    def get_separator_line() -> str:
        prefix = ('─'*8 + '┼')
        width = get_terminal_width()
        main_len = width - len(prefix)
        return Console._format_separator(prefix + ('─' * main_len))

    @staticmethod
    def format_prefix(label: str, f: AbstractFormat) -> str:
        return f(f'{label!s:>8.8s}') + Console.get_separator() + ' '

    @staticmethod
    def format_prefix_with_offset(offset: int, f: AbstractFormat = fmt.green) -> str:
        return Console.format_prefix(Console.format_offset(offset), f)

    @staticmethod
    def format_offset(offset: int) -> str:
        if Settings.decimal_offsets:
            return f'{offset:d}'
        return f'0x{offset:0{ceil(len(str(offset))/2)*2}x}'

    @staticmethod
    def print(s: str, end='\n', **kwargs):
        print(s, end=end, **kwargs)

    @staticmethod
    def _format_separator(s: str) -> str:
        return autof(seq.GRAY)(s) if Settings.debug > 0 else fmt.cyan(s)
