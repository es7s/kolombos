import abc
from typing import Optional

from pytermor import seq
from pytermor.fmt import AbstractFormat


class Marker(metaclass=abc.ABCMeta):
    def __init__(self, marker_char: str):
        self._marker_char = marker_char

    def __repr__(self):
        return f'{self.__class__.__name__}[{self._marker_char}]'

    @staticmethod
    def make(marker_char: str, opening_seq: Optional[SequenceSGR] = None) -> str:
        return f'{seq.RESET}{opening_seq if opening_seq else ""}{marker_char}{seq.RESET}'

    @property
    def marker_char(self) -> str:
        return self._marker_char

    @abc.abstractmethod
    def get_fmt(self) -> AbstractFormat: raise NotImplementedError
