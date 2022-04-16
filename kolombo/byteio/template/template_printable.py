from __future__ import annotations

from pytermor.seq import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, DisplayMode, ReadMode


class PrintableCharTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.PRINTABLE_CHAR, opening_seq, label)

    def _process_byte(self, b: int, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        default_label = super()._process_byte(b, display_mode, read_mode)

        if display_mode is DisplayMode.IGNORED:
            return default_label

        return chr(b)
