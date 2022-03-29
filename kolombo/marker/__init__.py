import abc
from typing import Optional

from pytermor import SGRSequence, Format, RESET


class Marker(metaclass=abc.ABCMeta):
    def __init__(self, marker_char: str):
        self._marker_char = marker_char

    @staticmethod
    def make(marker_char: str, opening_seq: Optional[SGRSequence] = None) -> str:
        return f'{RESET}{opening_seq if opening_seq else ""}{marker_char}{RESET}'

    @property
    def marker_char(self) -> str:
        return self._marker_char

    @abc.abstractmethod
    def get_fmt(self) -> Format: raise NotImplementedError
