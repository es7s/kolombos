from __future__ import annotations

import abc
import re
from typing import AnyStr, Union, List, Match

from pytermor import StringFilter, apply_filters

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

        self._filter_sgr = StringFilter(  # CSI (incl. SGR) sequences
            lambda s: re.sub(r'\x1b(\[)([0-9;:<=>?]*)([@A-Za-z\[])', self._format_csi_sequence, s)
        )  # @TODO group 3  ^^^^^^^^^^^^^^^^^^  : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
        self._filter_nf = StringFilter(  # nF Escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x2f])([\x20-\x2f]*)([\x30-\x7e])', self._format_generic_escape_sequence, s)
        )
        self._filter_esq = StringFilter(  # other escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x7f])()()', self._format_generic_escape_sequence, s)
        )
        self._filter_control = StringFilter(  # control chars incl. standalone escapes
            lambda s: re.sub(r'([\x00-\x08\x0e-\x1f\x7f])', self._format_control_char, s)
        )

        self._filters_fixed = [
            self._filter_sgr, self._filter_nf, self._filter_esq, self._filter_control
        ]
        self._filters_post = [

        ]

        self._control_char_map = ConfidentDict({
            k: MarkerRegistry.get_control_marker(k) for k in self.CONTROL_CHARCODES
        })

    @abc.abstractmethod
    def get_fallback_char(self) -> AnyStr: raise NotImplementedError

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
    def _format_csi_sequence(self, match: Match) -> AnyStr: raise NotImplementedError

    def _format_generic_escape_sequence(self, match: Match) -> AnyStr:
        if Settings.ignore_control:
            return self.get_fallback_char() + match.group(0)

        introducer = match.group(1)
        info = ''
        if Settings.effective_info_level() >= 1:
            info = introducer
        if Settings.effective_info_level() >= 2:
            info = match.group(0)
        # if introducer == ' ':
        #    introducer = FormatRegistry.marker_space.marker_char
        charcode = ord(introducer)
        marker = MarkerRegistry.get_esq_marker(charcode)
        return marker.print() + info

    def _format_control_char(self, match: Match) -> AnyStr:
        if Settings.ignore_control:
            return self.get_fallback_char()
        charcode = ord(match.group(0))
        marker = self._control_char_map.require_or_die(charcode)
        self._add_marker_match(MarkerMatch(match, marker))
        return marker.print()
