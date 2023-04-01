# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR, Seqs

from . import Template
from .. import CharClass, OpeningSeqPOV, LabelPOV, DisplayMode
from ...settings import Settings


class WhitespaceTemplate(Template):
    def __init__(self, label: str | LabelPOV = ''):
        super().__init__(CharClass.WHITESPACE, Seqs.HI_CYAN, label)

    def _get_focused_seq(self, app_settings: Settings) -> SequenceSGR:
        if app_settings.blink_focused:
            return Seqs.HI_CYAN + Seqs.BG_BLACK + Seqs.BLINK_DEFAULT
        return Seqs.BG_CYAN + Seqs.BLACK
