from __future__ import annotations

from typing import Match

from pytermor import SequenceSGR

from . import EscapeSequenceTemplate


class EscapeSequenceSGRTemplate(EscapeSequenceTemplate):
    def _get_brief_details_processed(self, m: Match) -> str:
        return m.group(6).decode('ascii')

    def _get_details_opening_seq(self, m: Match):
        params = m.group(6).decode('ascii').split(';')
        params_filtered = [
            int(p) for p in params if p and (30 <= int(p) <= 37 or 40 <= int(p) <= 47)
        ]
        return SequenceSGR(*params_filtered) + self.MARKER_DETAILS_SEQ
