from __future__ import annotations

from pytermor.seq import SequenceSGR

from . import _opt_arg


class Segment:
    def __init__(self, raw: bytes, processed: str, opening: SequenceSGR = None, type_label: str = None):
        self._raw = raw
        self._processed = processed
        self._opening = _opt_arg(opening)
        self._type_label = type_label

    @property
    def raw(self) -> bytes: return self._raw
    @property
    def processed(self) -> str: return self._processed
    @property
    def opening(self) -> SequenceSGR: return self._opening
    @property
    def type_label(self) -> str: return self._type_label
