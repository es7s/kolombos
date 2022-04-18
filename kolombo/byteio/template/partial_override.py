from __future__ import annotations

from typing import TypeVar, Generic, Dict, Any

from pytermor import SequenceSGR

T = TypeVar('T')


class PartialOverride(Generic[T]):
    def __init__(self, default: T, override: Dict[Any, T] = None):
        self._default: T = default
        self._override: Dict[Any, T]|None = override

    # returns first found element, iterates through arguments
    # from left to right (i.e. first key -> highest priority)
    def get(self, *keys: Any) -> T:
        if self._override:
            for key in keys:
                if key in self._override.keys():
                    return self._override[key]
        return self._default

    def set(self, key: Any, value: T):
        if not self._override:
            self._override = dict()
        self._override[key] = value

    def has_key(self, key: Any) -> bool:
        if not self._override:
            return False
        return key in self._override.keys()


OpeningSeqPOV = PartialOverride[SequenceSGR]
LabelPOV = PartialOverride[str]
