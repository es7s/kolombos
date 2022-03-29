from pytermor import Format, build_text256_seq, RESET
from pytermor.preset import OVERLINED, INVERSED

from . import Marker
from ..settings import Settings


class MarkerSGRReset(Marker):
    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._fmt = Format(OVERLINED + build_text256_seq(231), reset=True)
        self._fmt_focused = Format(INVERSED + build_text256_seq(231), reset=True)

    def print(self):
        return str(RESET) + self.get_fmt()(self._marker_char)

    def get_fmt(self) -> Format:
        if Settings.focus_esc:
            return self._fmt_focused
        return self._fmt
