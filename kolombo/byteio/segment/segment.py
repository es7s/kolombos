from __future__ import annotations

from kolombo.byteio.segment.template import SegmentTemplate
from kolombo.byteio.segment import Chainable
from kolombo.error import SegmentError


class Segment(Chainable):
    def __init__(self, template: SegmentTemplate, raw: bytes, processed: str = None):
        self._template = template
        self._raw = raw
        self._processed = processed

    def split(self, num_bytes: int) -> Segment:
        if not self.is_consistent:
            raise SegmentError('Unknown how to split inconsistent segment')

        left = Segment(self._template, self._raw[:num_bytes], self._processed[:num_bytes])

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
    def template(self) -> SegmentTemplate:
        return self._template

    @property
    def raw(self) -> bytes:
        return self._raw

    @property
    def processed(self) -> str:
        return self._processed

    def __eq__(self, other: Segment):
        if not isinstance(other, Segment):
            return False

        return self._template == other._template \
               and self._raw == other._raw \
               and self._processed == other._processed

    def __repr__(self):
        return f'{self.__class__.__name__}[{self._raw.hex(" ")}]->[{self._processed}]'
