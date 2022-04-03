from pytermor import build_c256, seq, autof
from pytermor.fmt import Format

from . import Marker
from ..settings import Settings


class MarkerSGRReset(Marker):
    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._fmt = autof(build_c256(231) + seq.OVERLINED)
        self._fmt_focused = autof(build_c256(231) + seq.INVERSED)

    def print(self):
        return str(seq.RESET) + self.get_fmt()(self._marker_char)

    def get_fmt(self) -> Format:
        if Settings.focus_esc:
            return self._fmt_focused
        return self._fmt
