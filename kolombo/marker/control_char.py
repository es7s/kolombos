from pytermor import seq
from pytermor.fmt import Format
from pytermor.seq import SequenceSGR

from . import Marker
from ..settings import Settings


class MarkerControlChar(Marker):
    def __init__(self, marker_char: str, opening_seq: SequenceSGR, no_focus: bool = False):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq, hard_reset_after=True)
        self._fmt_focused = Format(opening_seq + seq.INVERSED, hard_reset_after=True)
        self._no_focus = no_focus

    def print(self, *tpl_args):
        marker = self.marker_char.format(*tpl_args)
        return self.get_fmt()(marker)

    def get_fmt(self) -> Format:
        if self._no_focus:
            return self._fmt
        if Settings.focus_control:
            return self._fmt_focused
        return self._fmt
