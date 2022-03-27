from pytermor import SGRSequence, Format
from pytermor.preset import OVERLINED, INVERSED, BG_BLACK, RESET

from . import Marker
from ..settings import Settings


class MarkerEscapeSeq(Marker):
    def __init__(self, marker_char: str, opening_seq: SGRSequence):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq + OVERLINED, reset=True)
        self._fmt_focused = Format(opening_seq + INVERSED + BG_BLACK, reset=True)

    def print(self, additional_info: str = ''):
        return RESET.str + self.get_fmt()(self._marker_char + additional_info)

    def get_fmt(self) -> Format:
        if Settings.focus_esc:
            return self._fmt_focused
        return self._fmt
