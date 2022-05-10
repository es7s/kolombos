# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR

from . import Template
from .. import CharClass, OpeningSeqPOV, LabelPOV


class PrintableCharTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.PRINTABLE_CHAR, opening_seq, label)

    def _process_byte(self, b: int) -> str:
        if self._display_mode.is_ignored:
            return super()._process_byte(b)

        return chr(b)
