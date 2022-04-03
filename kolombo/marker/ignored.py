from pytermor.fmt import Format
from pytermor.seq import SequenceSGR

from . import Marker


class MarkerIgnored(Marker):
    def __init__(self, marker_char: str, opening_seq: SequenceSGR):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq, hard_reset_after=True)

    def print(self):
        return self.get_fmt()(self._marker_char)

    def get_fmt(self) -> Format:
        return self._fmt

