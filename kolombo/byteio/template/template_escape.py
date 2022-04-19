from __future__ import annotations

from typing import Match, List

from pytermor import SequenceSGR, seq

from . import OpeningSeqPOV, LabelPOV, Template
from .. import CharClass, MarkerDetailsEnum
from ..segment import Segment


class EscapeSequenceTemplate(Template):
    ESQ_MARKER_LABEL_SEQ: SequenceSGR = seq.OVERLINED

    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(CharClass.ESCAPE_SEQ, opening_seq, label)

    def substitute(self, m: Match, raw: bytes) -> List[Segment]:
        if self._display_mode.is_ignored:
            return super().substitute(m, raw)

        self._substituted.clear()

        label_raw = raw[:1]   # label of escape sequence is always 1-byte
        params_raw = raw[1:]  # @TODO replace space in CSI params to placeholder

        primary_seg = self._create_primary_segment(
            self._get_label_opening_seq(),
            label_raw,
            self._process(m, label_raw)
        )
        self._substituted.insert(0, primary_seg)
        self._fill_additional_segments(m, params_raw)

        return self._substituted

    def _fill_additional_segments(self, m: Match, params_raw: bytes):
        if self._marker_details is MarkerDetailsEnum.NO_DETAILS:
            return

        params_processed = params_raw.decode('ascii')

        if self._marker_details is MarkerDetailsEnum.BRIEF_DETAILS:
            params_processed = self._get_brief_details_processed(m)

        self._substituted.append(
            self._create_details_segment(params_raw, params_processed, m)
        )

    def _get_brief_details_processed(self, m: Match) -> str:
        return ''

    def _get_label_opening_seq(self) -> SequenceSGR:
        return self._opening_seq_stack.get(self._display_mode, self._read_mode) + self.ESQ_MARKER_LABEL_SEQ

    def _get_details_opening_seq(self, m: Match) -> SequenceSGR:
        return self._opening_seq_stack.get() + self.DETAILS_OPENING_SEQ