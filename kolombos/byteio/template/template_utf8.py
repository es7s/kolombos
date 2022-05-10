# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR

from . import Template
from .. import CharClass, OpeningSeqPOV, LabelPOV


class Utf8SequenceTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.UTF_8_SEQ, opening_seq, label)

    def _process(self, raw: bytes) -> str:
        default = lambda: super(type(self), self)._process(raw)

        if self._display_mode.is_ignored:
            return default()

        if self._read_mode.is_text or self._decode:
            decoded = raw.decode('utf8', errors='replace')
            if self._read_mode.is_binary:
                if len(decoded) < len(raw):
                    decoded = decoded.rjust(len(raw), '_')
                elif len(decoded) > len(raw):
                    decoded = decoded[:len(raw)]
            return decoded

        return default()
