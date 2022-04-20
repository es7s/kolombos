# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import Match

from pytermor import SequenceSGR, sgr
from pytermor.sgr import *

from . import EscapeSequenceTemplate, OpeningSeqPOV, LabelPOV


# noinspection PyMethodMayBeStatic
from ...settings import SettingsManager


class EscapeSequenceSGRTemplate(EscapeSequenceTemplate):
    ALLOWED_SGRS_FOR_MARKER_FORMAT = [  # INVERSED, UNDERLINED, OVERLINED are reserved for markers themself
        BOLD, DIM, ITALIC,
        CROSSLINED,
        *LIST_ALL_COLORS,
    ]

    def __init__(self, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        super().__init__(opening_seq, label)

    def _get_sgr_params(self, m: Match):
        return m.group(6).decode('ascii')

    def _get_brief_details_processed(self, m: Match) -> str:
        return self._get_sgr_params(m)

    def _get_details_opening_seq(self, m: Match) -> SequenceSGR:
        if SettingsManager.app_settings.no_color_markers:
            return self.DETAILS_OPENING_SEQ

        params = self._get_sgr_params(m).split(';')
        pcodes = [int(p) for p in params if p]
        pcodes_allowed = []
        while len(pcodes):
            pcode = pcodes.pop(0)
            if pcode == sgr.COLOR_EXTENDED or pcode == sgr.BG_COLOR_EXTENDED:
                if len(pcodes) >= 2 and pcodes[0] == sgr.EXTENDED_MODE_256:
                    pcodes_allowed.extend([pcode, pcodes.pop(0), pcodes.pop(0)])
                    continue
                if len(pcodes) >= 4 and pcodes[0] == sgr.EXTENDED_MODE_RGB:
                    pcodes_allowed.extend([pcode, *[pcodes.pop(0) for _ in range(4)]])
                    continue
            elif pcode in self.ALLOWED_SGRS_FOR_MARKER_FORMAT:
                pcodes_allowed.append(pcode)

        return self.DETAILS_OPENING_SEQ + SequenceSGR(*pcodes_allowed)
