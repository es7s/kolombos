# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import SequenceSGR, sgr, seq
from pytermor.sgr import *

from . import EscapeSequenceTemplate
from .. import OpeningSeqPOV, LabelPOV, MarkerDetailsEnum
from ...settings import SettingsManager


# noinspection PyMethodMayBeStatic
class EscapeSequenceSGRTemplate(EscapeSequenceTemplate):
    M1_SEPARATOR = '･'

    ALLOWED_SGRS_FOR_MARKER_FORMAT = [  # INVERSED, BOLD, UNDERLINED are reserved for markers themself
        DIM, ITALIC,
        OVERLINED, CROSSLINED,
        *LIST_ALL_COLORS,
    ]

    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(opening_seq, label)
        self._details_fmt_str: str|None = None
        self._brief_details_processed: str|None = None
        self._details_opening_seq: SequenceSGR|None = None

    def get_details_fmt_str(self) -> str:
        if self._details_fmt_str is None:
            raise ValueError('Details format not initialzied')
        return self._details_fmt_str

    def set_details_fmt_str(self, s: bytes):
        self._details_fmt_str = s.decode('ascii')

        params = self._details_fmt_str.split(';')
        pcodes = [int(p) for p in params if p]
        pcodes_allowed = []
        brief_names = []
        while len(pcodes):  # @TODO automatically set black/white text if only bg color is defined, and vice versa
            pcode = pcodes.pop(0)

            if pcode == sgr.COLOR_EXTENDED or pcode == sgr.BG_COLOR_EXTENDED:
                brief_type = 'F' if pcode == sgr.COLOR_EXTENDED else 'B'
                if len(pcodes) >= 2 and pcodes[0] == sgr.EXTENDED_MODE_256:
                    pcodes_allowed.extend([pcode, pcodes.pop(0), pcodes.pop(0)])
                    brief_names.append(f'{brief_type}{pcodes_allowed[-1]}')
                    continue
                if len(pcodes) >= 4 and pcodes[0] == sgr.EXTENDED_MODE_RGB:
                    pcodes_allowed.extend([pcode, *[pcodes.pop(0) for _ in range(4)]])
                    brief_names.append(
                        f'{brief_type}'
                        f'{pcodes_allowed[-3] * 256 * 256 + pcodes_allowed[-2] * 256 + pcodes_allowed[-1]:06x}'
                    )
                    continue
            elif pcode in self.ALLOWED_SGRS_FOR_MARKER_FORMAT:
                pcodes_allowed.append(pcode)
            brief_names.append(pcode)

        self._brief_details_processed = f'{seq.UNDERLINED_OFF}{self.M1_SEPARATOR}{seq.UNDERLINED}'.join(str(bn) for bn in brief_names)
        self._details_opening_seq = SequenceSGR(*pcodes_allowed)

    def _get_brief_details_processed(self) -> str:
        if self._brief_details_processed is not None:
            return self._brief_details_processed
        return self.get_details_fmt_str()

    def _get_label_opening_seq(self) -> SequenceSGR:
        if self._marker_details is MarkerDetailsEnum.NO_DETAILS and not SettingsManager.app_settings.no_color_markers:
            return super()._get_label_opening_seq() + self._details_opening_seq + self.ESQ_MARKER_LABEL_SEQ
        return super()._get_label_opening_seq()

    def _get_details_opening_seq(self) -> SequenceSGR:
        if SettingsManager.app_settings.no_color_markers:
            return self.DETAILS_OPENING_SEQ
        return self.DETAILS_OPENING_SEQ + self._details_opening_seq
