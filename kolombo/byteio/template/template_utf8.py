from __future__ import annotations

from pytermor import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, DisplayMode, ReadMode
from ...settings import SettingsManager


class Utf8SequenceTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.UTF_8_SEQ, opening_seq, label)

    def _process(self, raw: bytes, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        default_processed = super()._process(raw, display_mode, read_mode)

        if display_mode.is_ignored:
            return default_processed

        if read_mode.is_text or SettingsManager.app_settings.decode:
            decoded = raw.decode('utf8', errors='replace')
            if read_mode.is_binary:
                if len(decoded) < len(raw):
                    decoded = decoded.rjust(len(raw), '_')
                elif len(decoded) > len(raw):
                    decoded = decoded[:len(raw)]
            return decoded

        return default_processed
