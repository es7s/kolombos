import sys
from math import ceil
from typing import Any, List

from pytermor import fmt, seq

from kolombo.settings import Settings


def get_terminal_width() -> int:
    try:
        import shutil as _shutil
        width = _shutil.get_terminal_size().columns - 2
        return width
    except ImportError:
        return 80


def println(n: int = 1):
    print('\n'*n, end='')


# @TODO refactor, move to COnsole
def printd(v: Any, max_input_len: int = 5) -> str:
    if Settings.debug_buffer_contents_full:
        max_input_len = sys.maxsize

    if hasattr(v, 'preview'):
        v = v.preview(max_input_len)

    if isinstance(v, (bytes, List)):
        result = 'len ' + fmt.bold(str(len(v)))
        if not Settings.debug_buffer_contents:
            return result

        if len(v) == 0:
            return f'{result} {seq.GRAY}[]{seq.COLOR_OFF}'
        if isinstance(v, bytes):
            v = ' '.join([f'{b:02x}' for b in v])
        return f'{result} ' + \
               f'{seq.GRAY}[' + \
               f'{v[:2*(max_input_len-1)]}' + \
               (('.. ' + ''.join(v[-2:] )if len(v) > 2*(max_input_len - 1) else '')) + \
               f']{seq.COLOR_OFF}'

    return f'{v!s}'
