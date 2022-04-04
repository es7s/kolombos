from pytermor import autof, seq
from pytermor.fmt import Format

from . import Marker
from ..settings import Settings


class MarkerUTF8(Marker):
    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._fmt = autof(seq.HI_BLUE)
        self._fmt_focused = autof(seq.HI_BLUE + seq.INVERSED)

    def print(self):
        return self.get_fmt()(self._marker_char)

    def get_fmt(self) -> Format:
        if Settings.focus_utf8:
            return self._fmt_focused
        return self._fmt

