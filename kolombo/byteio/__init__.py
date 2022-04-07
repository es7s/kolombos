import re
from enum import Enum

from pytermor import fmt
from pytermor.fmt import Format

from kolombo.byteio.segment.segment import Segment
from kolombo.console import printd


class ReadMode(Enum):
    TEXT = 'text'
    BINARY = 'binary'


def align_offset(offset: int) -> str:
    return printd(offset).rjust(8)


def print_offset(offset: int, addr_fmt: Format):
    aligned = align_offset(offset)
    return addr_fmt(aligned) + fmt.cyan('│')

