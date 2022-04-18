from __future__ import annotations

from pytermor import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, DisplayMode, ReadMode


class NewlineTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.WHITESPACE, opening_seq, label)

    def _process_byte(self, b: int, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        default_label = super()._process_byte(b, display_mode, read_mode)

        if display_mode.is_ignored and read_mode.is_text:
            return default_label+chr(b)  # actual \n

        return default_label
