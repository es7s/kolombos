# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR, Seqs
from .template_whitespace import WhitespaceTemplate
from .. import OpeningSeqPOV, LabelPOV


class NewlineTemplate(WhitespaceTemplate):
    def __init__(self, label: str | LabelPOV = ''):
        super().__init__(label)

    def _process_byte(self, b: int) -> str:
        default = super()._process_byte(b)

        if self._read_mode.is_text:
            if self._display_mode.is_ignored:
                return f'{default}\n'   # line breaks must be printed even if char class is ignored

            return f'{default}{Seqs.RESET}\n'  # prevent colored bg overlapping between lines

        return default
