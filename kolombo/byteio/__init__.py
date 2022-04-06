import re
from enum import Enum

from pytermor import fmt
from pytermor.fmt import Format

from kolombo.byteio.segment.segment import Segment


class ReadMode(Enum):
    TEXT = 'text'
    BINARY = 'binary'


def align_offset(offset: int) -> str:
    return f'{offset:6}'


def print_offset(offset: int, addr_fmt: Format):
    aligned = align_offset(offset)
    return addr_fmt(aligned) + fmt.cyan('│  ')

