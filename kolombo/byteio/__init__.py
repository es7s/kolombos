import re
from enum import Enum

from pytermor import fmt
from pytermor.fmt import Format

from kolombo.byteio.segment.segment import Segment
from kolombo.settings import Settings


class ReadMode(Enum):
    TEXT = 'text'
    BINARY = 'binary'


def align_offset(offset: int) -> str:
    return f'0x{offset:08}{"":3s}'


def print_offset(offset: int, addr_fmt: Format):
    aligned = align_offset(offset)
    return re.sub(r'(0x0*)(\S+)(\s)',
                  addr_fmt(fmt.dim(r'\1') + r'\2') + fmt.cyan('│'),
                  aligned)


def print_offset_debug(prefix: str, start: int, payload: ):
    if Settings.debug < 2:
        return ''
    prefix = f'{prefix:2.2s}'
    return fmt.blue(prefix) + \
           fmt.cyan(f'{start:d}'.rjust(10 - len(prefix)) +
                    f'│{"":2s}' +
                    span.hex(' ')
                    ) + '\n'
