from __future__ import annotations

from pytermor import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass


class PrintableCharTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.PRINTABLE_CHAR, opening_seq, label)

    def _process_byte(self, b: int) -> str:
        if self._display_mode.is_ignored:
            return super()._process_byte(b)

        return chr(b)
