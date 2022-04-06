from __future__ import annotations

from typing import Tuple

from pytermor import autof
from pytermor.seq import SequenceSGR

from . import _opt_arg


class Segment:
    def __init__(self, raw: bytes, processed: str, opening: SequenceSGR = None, type_label: str = None):
        self._raw = raw
        self._processed = processed
        self._opening = _opt_arg(opening)
        self._closing = autof(self._opening).closing
        self._type_label = type_label

        self._cursor = 0
        self._is_closed = False

    def __repr__(self):
        return '{}[{}, {:.14s}, {!r}, {:.14s}]'.format(
            self.__class__.__name__,
            self._type_label,
            self._raw.hex(' '),
            self._opening,
            self._processed.encode().hex(' '),
            id(self),
        )

    def read_all(self, close: bool = True) -> Tuple[bytes, str]:
        if close:
            self._cursor = len(self._raw)
            self._is_closed = True
        return self._raw, f'{self._opening}{self._processed}{self._closing}'

    def read(self, n: int) -> Tuple[bytes, str]|None:
        if len(self._raw) != len(self._processed):
            raise RuntimeError('Non-consistent segments cannot use cursors')
        if self._is_closed:
            return

        cur_pos = self._cursor
        self._cursor = min(self._cursor + n, len(self._raw))
        if self._cursor >= len(self._raw):
            self._is_closed = True

        raw_part = self._raw[cur_pos:self._cursor]
        processed_part = '{}{}{}'.format(
            self._opening if cur_pos == 0 else '',
            self._processed[cur_pos:self._cursor],
            self._closing if self._is_closed else ''
        )
        return raw_part, processed_part

    @property
    def opening(self) -> SequenceSGR: return self._opening
    @property
    def type_label(self) -> str: return self._type_label

    @property
    def is_closed(self) -> bool: return self._is_closed
    @property
    def bytes_left(self) -> int: return len(self._raw) - self._cursor
