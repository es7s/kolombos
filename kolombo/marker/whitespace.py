from typing import Optional

from pytermor import fmt, seq
from pytermor.fmt import Format

from . import Marker
from ..settings import Settings


class MarkerWhitespace(Marker):
    _fmt = fmt.dim
    _fmt_focused = Format(seq.BG_CYAN + seq.BLACK, hard_reset_after=True)

    def __init__(self, marker_char: str, marker_char_focused_override: Optional[str] = None):
        super().__init__(marker_char)
        self._marker_char_focused = (marker_char_focused_override if marker_char_focused_override else marker_char)

    def print(self):
        return self.get_fmt()(self.marker_char)

    # нет времени объяснять, срочно костылим
    def get_fmt(self) -> Format:
        return self.sget_fmt()

    @staticmethod
    def sget_fmt() -> Format:
        if Settings.focus_space:
            return MarkerWhitespace._fmt_focused
        return MarkerWhitespace._fmt

    @property
    def marker_char(self) -> str:
        if Settings.focus_space:
            return self._marker_char_focused
        return self._marker_char
