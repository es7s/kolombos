from __future__ import annotations

import abc

from .. import ReadMode
from ..chain import ChainBuffer
from ..parser_buf import ParserBuffer


class FormatterFactory:
    @staticmethod
    def create(mode: ReadMode, *args) -> AbstractFormatter:
        from .binary import BinaryFormatter
        from .text import TextFormatter

        if mode is ReadMode.TEXT:
            return TextFormatter(*args)
        elif mode is ReadMode.BINARY:
            return BinaryFormatter(*args)
        raise RuntimeError(f'Invalid read mode {mode}')


# noinspection PyMethodMayBeStatic
class AbstractFormatter(metaclass=abc.ABCMeta):
    CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
    WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]
    PRINTABLE_CHARCODES = list(range(0x21, 0x7f))
    BINARY_CHARCODES = list(range(0x80, 0x100))

    def __init__(self, parser_buffer: ParserBuffer, chain_buffer: ChainBuffer):
        self._parser_buffer = parser_buffer
        self._chain_buffer = chain_buffer

    @abc.abstractmethod
    def format(self) -> str: raise NotImplementedError
