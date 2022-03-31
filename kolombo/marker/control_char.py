from pytermor import SequenceSGR, Format
from pytermor.preset import INVERSED, BG_BLACK

from . import Marker
from ..settings import Settings


class MarkerControlChar(Marker):
    def __init__(self, marker_char: str, opening_seq: SequenceSGR):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq, reset=True)
        self._fmt_focused = Format(opening_seq + INVERSED + BG_BLACK, reset=True)

    def print(self, *tpl_args):
        marker = self.marker_char.format(*tpl_args)
        return self.get_fmt()(marker)

    def get_fmt(self) -> Format:
        if Settings.focus_control:
            return self._fmt_focused
        return self._fmt
