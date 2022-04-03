from __future__ import annotations

import abc
import re
from typing import AnyStr, Union, List, Match, Pattern

from pytermor.util import StringFilter, apply_filters

from ..marker.registry import MarkerRegistry
from ..settings import Settings
from ..util import ConfidentDict, MarkerMatch
from ..writer import Writer


# noinspection PyMethodMayBeStatic
class AbstractFormatter(metaclass=abc.ABCMeta):
    CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
    WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]

    def __init__(self, _writer: Writer):
        self._writer = _writer

        self._filter_sgr = StringFilter[str](  # CSI (incl. SGR) sequences
            lambda s: re.sub(r'\x1b(\[)([0-9;:<=>?]*)([@A-Za-z\[])', self._format_csi_sequence, s)
        )  # @TODO group 3  ^^^^^^^^^^^^^^^^^^  : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
        self._filter_nf = StringFilter[str](  # nF Escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x2f])([\x20-\x2f]*)([\x30-\x7e])', self._format_generic_escape_sequence, s)
        )
        self._filter_esq = StringFilter[str](  # other escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x7f])()()', self._format_generic_escape_sequence, s)
        )
        self._filter_control = StringFilter[str](  # control chars incl. standalone escapes
            lambda s: re.sub(self._get_filter_control(), self._format_control_char, s)
        )  # костыль. разобраться
        self._filter_restore_sgrs = StringFilter[str](
            lambda s: re.sub(r'\x1b\xff', '\x1b', s)
        )
        self._filter_space = StringFilter[str](  # space character
            lambda s: re.sub(r'(\x20+)', self._format_space, s)
        )
        self._filter_whitespace = StringFilter[str](  # whitespace excl. space char
            lambda s: re.sub(r'([\t\n\v\f\r])', self._format_whitespace, s)
        )

        self._filters_fixed = [
            self._filter_sgr, self._filter_nf, self._filter_esq,
            self._filter_control, self._filter_restore_sgrs,
            self._filter_space, self._filter_whitespace,
        ]
        self._filters_post = []

        self._control_char_map = ConfidentDict({
            k: MarkerRegistry.get_control_marker(k) for k in self.CONTROL_CHARCODES
        })
        self._whitespace_map = {}

    @abc.abstractmethod
    def get_fallback_char(self) -> AnyStr: raise NotImplementedError

    @abc.abstractmethod
    def _get_filter_control(self) -> Pattern: raise NotImplementedError

    @abc.abstractmethod
    def format(self, raw_input: Union[AnyStr, List[AnyStr]], offset: int): raise NotImplementedError

    def _add_marker_match(self, mm: MarkerMatch):
        return

    def _process_input(self, decoded_input: str) -> str:
        return apply_filters(decoded_input, *self._filters_fixed)

    def _postprocess_input(self, decoded_input: str) -> str:
        return apply_filters(decoded_input, *self._filters_post)

    def _filter_sgr_param(self, p):
        return len(p) > 0 and p != '0'

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
