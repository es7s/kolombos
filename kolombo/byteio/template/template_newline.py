from __future__ import annotations

from pytermor import SequenceSGR, seq

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass


class NewlineTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.WHITESPACE, opening_seq, label)

    def _process_byte(self, b: int) -> str:
        default = super()._process_byte(b)

        if self._read_mode.is_text:
            if self._display_mode.is_ignored:
                return f'{default}\n'   # line breaks must be printed even if char class is ignored

            return f'{default}{seq.RESET}\n'  # prevent colored bg overlapping between lines

        return default
