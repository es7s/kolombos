from __future__ import annotations

from re import Match
from typing import List

from pytermor import seq, SequenceSGR, Format, autof

from . import PartialOverride, OpeningSeqPOV, LabelPOV
from .. import CharClass, DisplayMode
from ..const import TYPE_LABEL_MAP
from ..segment import Segment
from ...settings import SettingsManager


class Template:
    IGNORED_OPENING_SEQ: SequenceSGR = seq.GRAY + seq.DIM
    IGNORED_LABEL: str = '×'
    MARKER_DETAILS_SEQ: SequenceSGR = seq.BG_BLACK + seq.OVERLINED

    def __init__(self, char_class: CharClass, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        if not isinstance(opening_seq, PartialOverride):
            opening_seq = OpeningSeqPOV(opening_seq)
        if not isinstance(label, PartialOverride):
            label = LabelPOV(label)

        self._char_class: CharClass = char_class
        self._opening_seq_stack: OpeningSeqPOV = opening_seq
        self._label_stack: LabelPOV = label
        self._substituted: List[Segment] = []

        if not self._opening_seq_stack.has_key(DisplayMode.FOCUSED):
            self._opening_seq_stack.set(DisplayMode.FOCUSED, self._opening_seq_stack.get() + seq.INVERSED)
        if not self._opening_seq_stack.has_key(DisplayMode.IGNORED):
            self._opening_seq_stack.set(DisplayMode.IGNORED, self.IGNORED_OPENING_SEQ)

        if not self._label_stack.has_key(DisplayMode.IGNORED):
            self._label_stack.set(DisplayMode.IGNORED, self.IGNORED_LABEL)

        app_settings = SettingsManager.app_settings
        self._display_mode = app_settings.get_char_class_display_mode(self._char_class)
        self._read_mode = app_settings.read_mode

    def substitute(self, m: Match, raw: bytes) -> List[Segment]:
        self._substituted.clear()

        primary_seg = Segment(
            self._opening_seq_stack.get(self._display_mode, self._read_mode),
            TYPE_LABEL_MAP[self._char_class],
            raw,
            self._process(m, raw)
        )
        self._substituted.insert(0, primary_seg)
        return self._substituted

    def _process(self, m: Match, raw: bytes) -> str:
        return ''.join(self._process_byte(b) for b in raw)

    def _process_byte(self, b: int,) -> str:
        return self._label_stack.get(self._display_mode, self._read_mode)
