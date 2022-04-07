from __future__ import annotations

import abc
from typing import Match, Tuple

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

    def __init__(self, parser_buffer: ParserBuffer, data_flow: ChainBuffer):
        self._parser_buffer = parser_buffer
        self._chain_buffer = data_flow

    @abc.abstractmethod
    def format(self, offset: int) -> str: raise NotImplementedError

    @abc.abstractmethod
    def _format_csi_sequence(self, match: Match) -> str: raise NotImplementedError

    @abc.abstractmethod
    def _format_generic_escape_sequence(self, match: Match) -> str: raise NotImplementedError

    @abc.abstractmethod
    def _format_control_char(self, match: Match) -> str: raise NotImplementedError

    @abc.abstractmethod
    def _format_space(self, match: Match) -> str: raise NotImplementedError

    @abc.abstractmethod
    def _format_whitespace(self, match: Match) -> str: raise NotImplementedError
