from __future__ import annotations

from typing import Dict

from pytermor.seq import SequenceSGR

from kolombo.byteio.char_class import CharClass
from kolombo.byteio.display_mode import DisplayMode
from kolombo.byteio.read_mode import ReadMode
from kolombo.byteio.template.partial_override import OpeningSeqPOV, LabelPOV
from kolombo.byteio.template.template import Template
from kolombo.settings import SettingsManager, SettingsEnum


class PrintableCharTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.PRINTABLE_CHAR, opening_seq, label)

    def _process_byte(self, b: int, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        default_label = super()._process_byte(b, display_mode, read_mode)

        if display_mode is DisplayMode.IGNORED:
            return default_label

        return chr(b)
