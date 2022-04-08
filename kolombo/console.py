from __future__ import annotations

import sys
import traceback
from typing import List

from pytermor import autof, seq, fmt
from pytermor.fmt import Format, EmptyFormat

from .settings import Settings
from .util import get_terminal_width, printd


class ConsoleBuffer:
    def __init__(self, level: int = 1, key_prefix: str = None, offset_fmt: Format = fmt.green):
        self._buf = ''
        self._level = level

        self._default_prefix = Console.prefix(key_prefix, autof(seq.GRAY)) if key_prefix else None
        self._offset_fmt = offset_fmt

    def write(self, s: str, offset: int = None, end='\n', no_default_prefix=False, flush=True):
        prefix = ''
        if isinstance(offset, int):
            prefix = Console.prefix_offset(offset, self._offset_fmt)
        elif self._default_prefix is not None:
            if not no_default_prefix:
                prefix = self._default_prefix

        self._buf += f'{prefix}{s}{end}'
        if flush:
            self.flush()

    def flush(self):
        if not self._buf:
            return
        fmted = autof(seq.BG_BLACK)(self._buf)
        self._buf = ''

        Console.debug(fmted, level=self._level, end='')


class Console:
    FMT_WARNING = autof(seq.HI_YELLOW)
    FMT_ERROR_TRACE = fmt.red
    FMT_ERROR = autof(seq.HI_RED)

    buffers: List[ConsoleBuffer] = list()

    @staticmethod
    def register_buffer(buffer: ConsoleBuffer) -> ConsoleBuffer:
        Console.buffers.append(buffer)
        return buffer

    @staticmethod
    def flush_buffers():
        for buffer in Console.buffers:
            buffer.flush()

    @staticmethod
    def on_exception(e: Exception):
        Console.flush_buffers()
        if Settings.debug > 0:
            tb_lines = [line.rstrip('\n')
                        for line
                        in traceback.format_exception(e.__class__, e, e.__traceback__)]
            error = tb_lines.pop(-1)
            Console._print(Console.FMT_ERROR_TRACE('\n'.join(tb_lines)))
            Console.error(error)
        else:
            Console.error(f'{e.__class__.__name__}: {e!s}')
            Console.info("Run the app with '--debug' argument to see the details")

    @staticmethod
    def debug(s: str = '', level=1, end='\n'):
        if Settings.debug >= level:
            Console._print(s, end=end)

    @staticmethod
    def info(s: str = '', end='\n'):
        Console._print(s, end=end)

    @staticmethod
    def warn(s: str = '', end='\n'):
        Console._print(Console.FMT_WARNING(f'WARNING: {s}'), end=end)

    @staticmethod
    def error(s: str = '', end='\n'):
        Console._print(Console.FMT_ERROR(fmt.bold('ERROR: ') + s), end=end, file=sys.stderr)

    @staticmethod
    def separator():
        prefix = ('─'*8 + '┼')
        width = get_terminal_width()
        main_len = width - len(prefix)
        return prefix + ('─'*main_len)

    @staticmethod
    def prefix(label: str, f: Format):
        return f(f'{label!s:>8.8s}') + fmt.cyan('│ ')

    @staticmethod
    def prefix_offset(offset: int, f: Format = fmt.green):
        return Console.prefix(printd(offset), f)

    @staticmethod
    def _print(s: str, end='\n', **kwargs):
        print(s, end=end, **kwargs)
