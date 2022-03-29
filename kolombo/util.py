from __future__ import annotations

from typing import TypeVar, Dict, Match, AnyStr

from .marker import Marker
from .marker.sgr import MarkerSGR
from .settings import Settings

KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.


class ConfidentDict(Dict[KT, VT]):
    def find_or_die(self, key: KT) -> VT | None:
        if key not in self:
            raise LookupError(f'Key not found: {key}')
        return self[key]

    def require_or_die(self, key: KT) -> VT:
        val = self.find_or_die(key)
        if val is None:
            raise ValueError(f'Value is None: {key}')
        return val


class MarkerMatch:
    def __init__(self, match: Match, marker: Marker = None, overwrite: bool = False):
        self.match = match
        self.fmt = None
        self.marker_char = None
        if marker:
            self.set_marker(marker)

        self.overwrite = overwrite
        self.sgr_seq: AnyStr|None = None
        self.applied: bool = False

    def set_marker(self, marker: Marker):
        self.fmt = marker.get_fmt()
        self.marker_char = marker.marker_char

    def _format(self, source_text: str) -> str:
        if self.fmt is None:
            return source_text
        return self.fmt(source_text)

    def target_text_hex(self, source_text: str) -> str:
        return self._format(source_text)

    def target_text_processed(self, source_text: str) -> str:
        if self.overwrite:
            target_text = self._format(self.marker_char if self.marker_char else '?')
        else:
            target_text = self._format(source_text)

        if self.sgr_seq and not Settings.no_color_content:
            target_text += self.sgr_seq + str(MarkerSGR.PROHIBITED_CONTENT_SEQS)

        return target_text
