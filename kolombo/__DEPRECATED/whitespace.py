from typing import Optional

from pytermor import fmt, seq, autof
from pytermor.fmt import Format

from . import Marker
from ..settings import SettingsManager


class MarkerWhitespace(Marker):
    _fmt = fmt.dim
    _fmt_focused = autof(seq.BG_CYAN + seq.BLACK)

    def __init__(self, marker_char: str, marker_char_focused_override: Optional[str] = None):
        super().__init__(marker_char)
        self._marker_char_focused = (marker_char_focused_override if marker_char_focused_override else marker_char)

    def print(self):
        return self.get_fmt()(self.marker_char[0]) + self.marker_char[1:]

    # нет времени объяснять, срочно костылим
    def get_fmt(self) -> Format:
        return self.sget_fmt()

    @staticmethod
    def sget_fmt() -> Format:
        if SettingsManager.app_settings.focus_space:
            return MarkerWhitespace._fmt_focused
        return MarkerWhitespace._fmt

    @property
    def marker_char(self) -> str:
        if SettingsManager.app_settings.focus_space:
            return self._marker_char_focused
        return self._marker_char
