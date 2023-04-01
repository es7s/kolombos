# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR, Seqs
from . import Template
from .. import CharClass, LabelPOV, DisplayMode
from ...settings import Settings


class PrintableCharTemplate(Template):
    def __init__(self, label: str | LabelPOV = ''):
        super().__init__(CharClass.PRINTABLE_CHAR, SequenceSGR.init_color_indexed(102), label)

    def _process_byte(self, b: int) -> str:
        if self._display_mode.is_ignored:
            return super()._process_byte(b)
        return chr(b)

    def _get_focused_seq(self, app_settings: Settings) -> SequenceSGR:
        if app_settings.blink_focused:
            return self._opening_seq_stack.get() + Seqs.BLINK_DEFAULT
        return self._opening_seq_stack.get(DisplayMode.FOCUSED)
