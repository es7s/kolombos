# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import Dict, List

from pytermor import SequenceSGR

from . import Template
from .. import CharClass, MarkerDetailsEnum, OpeningSeqPOV, LabelPOV
from ..segment import Segment


class ControlCharGenericTemplate(Template):
    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.CONTROL_CHAR, opening_seq, label)

        self._brief_label_map: Dict[int, str] = {
            0x01: 'A', 0x02: 'B', 0x03: 'C',  0x04: 'D', 0x05: 'E', 0x06: 'F',
            0x07: 'G', 0x0e: 'N', 0x0f: 'O',  0x10: 'P', 0x11: 'Q', 0x12: 'R',
            0x13: 'S', 0x14: 'T', 0x15: 'U',  0x16: 'V', 0x17: 'W', 0x18: 'X',
            0x19: 'Y', 0x1a: 'Z', 0x1c: '\\', 0x1d: ']', 0x1e: '^', 0x1f: '_',
        }

    def substitute(self, raw: bytes) -> List[Segment]:
        self._substituted.clear()

        if self._marker_details is MarkerDetailsEnum.BINARY_STRICT or \
           self._marker_details is MarkerDetailsEnum.NO_DETAILS:
            self._substituted.append(self._create_primary_segment(
                self._opening_seq_stack.get(self._display_mode, self._read_mode),
                bytes(raw),
                self._process(raw),
            ))
            return self._substituted

        for label_raw in raw:
            label_processed = self._process_byte(label_raw)
            self._substituted.append(self._create_primary_segment(
                self._opening_seq_stack.get(self._display_mode, self._read_mode),
                bytes(label_raw),
                label_processed,
            ))
            self._fill_additional_segments(label_raw)

        return self._substituted

    def _fill_additional_segments(self, b: int):
        if self._display_mode.is_ignored:
            return

        if self._marker_details is MarkerDetailsEnum.BINARY_STRICT or \
           self._marker_details is MarkerDetailsEnum.NO_DETAILS:
            return

        elif self._marker_details is MarkerDetailsEnum.BRIEF_DETAILS:
            if b not in self._brief_label_map.keys():
                raise KeyError(f'No brief label defined for byte 0x{b:02x}')
            self._substituted.append(self._create_details_segment(b'', self._brief_label_map[b]))

        elif self._marker_details is MarkerDetailsEnum.FULL_DETAILS:
            self._substituted.append(self._create_details_segment(b'', '{:02x}'.format(b)))

        else:
            raise RuntimeError(f'Invalid marker details level: {self._marker_details.value}')

    def _get_details_opening_seq(self) -> SequenceSGR:
        return self._opening_seq_stack.get() + self.DETAILS_OPENING_SEQ
