from pytermor import seq
from pytermor.fmt import Format
from pytermor.seq import SequenceSGR

from . import Marker
from ..settings import Settings


class MarkerEscapeSeq(Marker):
    def __init__(self, marker_char: str, opening_seq: SequenceSGR):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq + seq.OVERLINED, hard_reset_after=True)
        self._fmt_focused = Format(opening_seq + seq.INVERSED + seq.BG_BLACK, hard_reset_after=True)

    def print(self, additional_info: str = ''):
        return seq.RESET.str + self.get_fmt()(self._marker_char + additional_info)

    def get_fmt(self) -> Format:
        if Settings.focus_esc:
            return self._fmt_focused
        return self._fmt
