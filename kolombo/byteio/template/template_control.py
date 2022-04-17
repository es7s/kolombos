from __future__ import annotations

from typing import Dict

from pytermor.seq import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, DisplayMode, ReadMode, MarkerDetailsEnum
from ...settings import SettingsManager


class ControlCharGenericTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.CONTROL_CHAR, opening_seq, label)

        self._marker_details = SettingsManager.app_settings.effective_marker_details
        self._brief_label_map: Dict[int, str] = {
            0x01: 'A', 0x02: 'B', 0x03: 'C',  0x04: 'D', 0x05: 'E', 0x06: 'F',
            0x07: 'G', 0x0e: 'N', 0x0f: 'O',  0x10: 'P', 0x11: 'Q', 0x12: 'R',
            0x13: 'S', 0x14: 'T', 0x15: 'U',  0x16: 'V', 0x17: 'W', 0x18: 'X',
            0x19: 'Y', 0x1a: 'Z', 0x1c: '\\', 0x1d: ']', 0x1e: '^', 0x1f: '_',
        }

    def _process_byte(self, b: int, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        default_label = super()._process_byte(b, display_mode, read_mode)

        if display_mode.is_ignored:
            return default_label

        if read_mode.is_binary or self._marker_details is MarkerDetailsEnum.NO_DETAILS:  # Ɐ
            return default_label

        if self._marker_details is MarkerDetailsEnum.BRIEF_DETAILS:  # ⱯZ
            if b not in self._brief_label_map.keys():
                raise KeyError(f'No brief label defined for byte 0x{b:02x}')
            return default_label + self._brief_label_map[b]

        if self._marker_details is MarkerDetailsEnum.FULL_DETAILS:  # Ɐ1a
            return default_label + f'{b:02x}'

        return default_label
