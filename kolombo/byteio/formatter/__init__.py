from __future__ import annotations

import abc
from typing import List, Match, Tuple

from .. import ReadMode
from ..segment.segment import Segment


class FormatterFactory:
    @staticmethod
    def create(mode: ReadMode) -> AbstractFormatter:
        from .binary import BinaryFormatter
        from .text import TextFormatter

        if mode is ReadMode.TEXT:
            return TextFormatter()
        elif mode is ReadMode.BINARY:
            return BinaryFormatter()
        raise RuntimeError(f'Invalid read mode {mode}')


# noinspection PyMethodMayBeStatic
class AbstractFormatter(metaclass=abc.ABCMeta):
    CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
    WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]
    PRINTABLE_CHARCODES = list(range(0x21, 0x7f))

    @abc.abstractmethod
    def format(self, segs: List[Segment], offset: int) -> Tuple[str, str|None]: raise NotImplementedError

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
