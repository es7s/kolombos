# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR

from . import Chainable


class Segment(Chainable):
    def __init__(self, opening_seq: SequenceSGR, type_label: str, raw: bytes, processed: str = None):
        self._opening_seq = opening_seq
        self._type_label = type_label
        self._raw = raw
        self._processed = processed

    def split(self, num_bytes: int) -> Segment:
        if not self.is_consistent:
            raise BufferError('Unknown how to split inconsistent segment. Usually this error means that app is operating'
                              'in binary mode, but for some reason template processing resulted in output with '
                              'different length (which is allowed for text mode only).')

        left = Segment(self._opening_seq, self._type_label, self._raw[:num_bytes], self._processed[:num_bytes])

        self._raw = self._raw[num_bytes:]
        self._processed = self._processed[num_bytes:]
        return left

    @property
    def data_len(self) -> int:
        return len(self._raw)

    @property
    def is_newline(self) -> bool:
        return '\n' in self._processed

    @property
    def is_consistent(self) -> bool:
        return len(self._raw) == len(self._processed)

    @property
    def type_label(self) -> str:
        return self._type_label

    @property
    def opening_seq(self) -> SequenceSGR:
        return self._opening_seq

    @property
    def raw(self) -> bytes:
        return self._raw

    @property
    def processed(self) -> str:
        return self._processed

    def __eq__(self, other: Segment):
        if not isinstance(other, Segment):
            return False

        return self._opening_seq == other._opening_seq \
               and self._type_label == other._type_label \
               and self._raw == other._raw \
               and self._processed == other._processed

    def __repr__(self):
        return f'{self.__class__.__name__}[{self._raw.hex(" ")}]->[{self._processed}]'
