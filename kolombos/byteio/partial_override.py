# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from copy import copy, deepcopy
from typing import TypeVar, Generic, Dict

from pytermor import SequenceSGR, NOOP_SEQ

from kolombos.byteio import ByteIOMode

KT = TypeVar('KT')
VT = TypeVar('VT')


class PartialOverride(Generic[KT, VT]):
    """Class used to reduce overhead when dealing with abstractions with
    lots of different parameter values, which are *almost always* equal
    to some default value.

    """
    def __init__(self, default: VT, override: Dict[KT, VT] = None):
        self._default: VT = default
        self._override: Dict[KT, VT]|None = override

    def get(self, *keys: KT) -> VT:
        """Returns first found override value, or default value if nothing
         found. Iterates through arguments from left to right (i.e. first
         `key` has the highest priority).

        """
        if self._override:
            for key in keys:
                if key in self._override.keys():
                    return self._override[key]
        return self._default

    def set(self, key: KT, value: VT):
        if not self._override:
            self._override = dict()
        self._override[key] = value

    def has_key(self, key: KT) -> bool:
        if not self._override:
            return False
        return key in self._override.keys()

    def clone(self) -> PartialOverride[KT, VT]:
        return self.__class__(self._default, {k: self._clone(v) for k, v in (self._override or {}).items()})

    def _clone(self, v: VT) -> VT:
        if isinstance(v, SequenceSGR):
            return SequenceSGR(*v.params)
        return copy(v)


OpeningSeqPOV = PartialOverride[ByteIOMode, SequenceSGR]

LabelPOV = PartialOverride[ByteIOMode, str]
