from math import ceil
from typing import Any, List

from pytermor import fmt, seq


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
    if hasattr(v, 'preview'):
        v = v.preview(max_input_len)

    if isinstance(v, (bytes, List)):
        length = 'len ' + fmt.bold(str(len(v)))
        if len(v) == 0:
            return f'{length} {seq.GRAY}[]{seq.COLOR_OFF}'
        if isinstance(v, bytes):
            v = ' '.join([f'{b:02x}' for b in v])
        return f'{length} ' + \
               f'{seq.GRAY}[' + \
               f'{v[:2*(max_input_len-1)]}' + \
               (('.. ' + ''.join(v[-2:] )if len(v) > 2*(max_input_len - 1) else '')) + \
               f']{seq.COLOR_OFF}'

    if isinstance(v, int):
        return f'{v:0{ceil(len(str(v))/4)*4}d}'
        return f'0x{v:0{ceil(len(str(v))/2)*2}x}'

    return f'{v!s}'
