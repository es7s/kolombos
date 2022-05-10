# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR

from . import Chainable


class SequenceRef(Chainable):
    def __init__(self, ref: SequenceSGR):
        self._ref: SequenceSGR = ref

    @property
    def data_len(self) -> int:
        return 0

    @property
    def is_newline(self) -> bool:
        return False

    @property
    def ref(self) -> SequenceSGR:
        return self._ref

    def __eq__(self, other):
        if not isinstance(other, SequenceRef):
            return False
        return self._ref == self._ref

    def __repr__(self):
        return f'{self.__class__.__name__}::{self._ref!r}'


class OneUseSequenceRef(SequenceRef):
    pass


class StartSequenceRef(SequenceRef):
    pass


class StopSequenceRef(SequenceRef):
    pass
