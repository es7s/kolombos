from __future__ import annotations

from typing import Callable

from . import Segment


class SegmentProcessor:
    def __init__(self, apply_sgr: bool, encode_sgr: bool, format_fn: Callable[[Segment], str]):
        self._apply_sgr = apply_sgr
        self._encode_sgr = encode_sgr
        self._format_fn = format_fn

    @property
    def apply_sgr(self):
        return self._apply_sgr

    @property
    def encode_sgr(self):
        return self._encode_sgr

    def format(self, segment: Segment) -> str:
        return self._format_fn(segment)
