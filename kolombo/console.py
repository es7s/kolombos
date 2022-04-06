from __future__ import annotations

import sys
import traceback

from pytermor import autof, seq, fmt

from kolombo.settings import Settings


class Console:
    FMT_WARNING = autof(seq.HI_YELLOW)
    FMT_ERROR_TRACE = fmt.red
    FMT_ERROR = autof(seq.HI_RED)

    @staticmethod
    def println(n: int = 1):
        print('\n'*n, end='')

    @staticmethod
    def on_exception(e: Exception):
        if Settings.debug > 0:
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
    def debug(s: str = '', ret: bool = False) -> str|None:
        return Console.debug_on(s, 1, ret)

    @staticmethod
    def debug_on(s: str = '', level: int = 1, ret: bool = False) -> str|None:
        if Settings.debug < level:
            return ''
        return Console._handle(s, ret)

    @staticmethod
    def print(s: str = '') -> str|None:
        return Console._handle(s, False)

    @staticmethod
    def info(s: str = '', ret: bool = False) -> str|None:
        return Console._handle(s, ret)

    @staticmethod
    def warn(s: str = '', ret: bool = False) -> str|None:
        return Console._handle(Console.FMT_WARNING(f'WARNING: {s}'), ret)

    @staticmethod
    def error(s: str = '', ret: bool = False) -> str|None:
        return Console._handle(Console.FMT_ERROR(fmt.bold('ERROR: ')+s), ret, file=sys.stderr)

    @staticmethod
    def _handle(s: str, ret: bool, **kwargs) -> str|None:
        if ret:
            return s
        print(s, **kwargs)
        return ''
