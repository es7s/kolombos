from enum import Enum

from pytermor import fmt

from kolombo.byteio.segment.segment import Segment


class ReadMode(Enum):
    TEXT = 'text'
    BINARY = 'binary'


def separator() -> str:
    return fmt.cyan('│')
