from __future__ import annotations

from typing import Dict

from pytermor import SequenceSGR

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, MarkerDetailsEnum
from ..segment import Segment
from ...settings import SettingsManager


class ControlCharGenericTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.CONTROL_CHAR, opening_seq, label)

        self._marker_details: MarkerDetailsEnum = SettingsManager.app_settings.effective_marker_details
        self._brief_label_map: Dict[int, str] = {
            0x01: 'A', 0x02: 'B', 0x03: 'C',  0x04: 'D', 0x05: 'E', 0x06: 'F',
            0x07: 'G', 0x0e: 'N', 0x0f: 'O',  0x10: 'P', 0x11: 'Q', 0x12: 'R',
            0x13: 'S', 0x14: 'T', 0x15: 'U',  0x16: 'V', 0x17: 'W', 0x18: 'X',
            0x19: 'Y', 0x1a: 'Z', 0x1c: '\\', 0x1d: ']', 0x1e: '^', 0x1f: '_',
        }

    def _process_byte(self, b: int) -> str:
        self._create_additional_segments(b)
        return super()._process_byte(b)

    def _create_additional_segments(self, b: int):  # @FIXME substitute one by one OR refactor segmentation mechanish
        if self._display_mode.is_ignored:
            return

        if self._marker_details is MarkerDetailsEnum.BINARY_STRICT or \
           self._marker_details is MarkerDetailsEnum.NO_DETAILS:
            return

        elif self._marker_details is MarkerDetailsEnum.BRIEF_DETAILS:  # ⱯZ
            if b not in self._brief_label_map.keys():
                raise KeyError(f'No brief label defined for byte 0x{b:02x}')
            self._substituted.append(Segment(self.MARKER_DETAILS_SEQ, '*', b'', self._brief_label_map[b]))
            return

        elif self._marker_details is MarkerDetailsEnum.FULL_DETAILS:  # Ɐ1a
            self._substituted.append(Segment(self.MARKER_DETAILS_SEQ, '*', b'', '{:02x}'.format(b)))

        else:
            raise RuntimeError(f'Invalid marker details level: {self._marker_details.value}')
