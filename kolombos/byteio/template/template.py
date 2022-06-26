# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import List

from pytermor import seq, SequenceSGR

from .. import CharClass, DisplayMode, MarkerDetailsEnum, ReadMode, PartialOverride, OpeningSeqPOV, LabelPOV
from ..const import TYPE_LABEL_MAP, TYPE_LABEL_DETAILS
from ..segment import Segment
from ...settings import SettingsManager


class Template:
    SEPARATOR_LEFT =  '⢸'
    SEPARATOR_RIGHT = '⡇'

    IGNORED_LABEL: str = '×'
    IGNORED_OPENING_SEQ: SequenceSGR = seq.GRAY + seq.DIM
    DETAILS_OPENING_SEQ: SequenceSGR = seq.BG_BLACK + seq.UNDERLINED

    def __init__(self, char_class: CharClass, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        if not isinstance(opening_seq, PartialOverride):
            opening_seq = OpeningSeqPOV(opening_seq)
        if not isinstance(label, PartialOverride):
            label = LabelPOV(label)

        self._char_class: CharClass = char_class
        self._opening_seq_stack: OpeningSeqPOV = opening_seq
        self._label_stack: LabelPOV = label
        self._substituted: List[Segment] = []

        self._display_mode: DisplayMode = DisplayMode.DEFAULT
        self._read_mode: ReadMode = ReadMode.TEXT
        self._marker_details: MarkerDetailsEnum = MarkerDetailsEnum.NO_DETAILS
        self._decode: bool = False

        if not self._opening_seq_stack.has_key(DisplayMode.FOCUSED):
            self._opening_seq_stack.set(DisplayMode.FOCUSED, self._opening_seq_stack.get() + seq.INVERSED)
        if not self._opening_seq_stack.has_key(DisplayMode.IGNORED):
            self._opening_seq_stack.set(DisplayMode.IGNORED, self.IGNORED_OPENING_SEQ)

        if not self._label_stack.has_key(DisplayMode.IGNORED):
            self._label_stack.set(DisplayMode.IGNORED, self.IGNORED_LABEL)

        self.update_settings()

    def update_settings(self):
        app_settings = SettingsManager.app_settings
        self._display_mode = app_settings.get_char_class_display_mode(self._char_class)
        self._read_mode = app_settings.read_mode
        self._marker_details = app_settings.effective_marker_details
        self._decode = app_settings.decode

    def substitute(self, raw: bytes) -> List[Segment]:
        self._substituted.clear()

        primary_seg = self._create_primary_segment(
            self._opening_seq_stack.get(self._display_mode, self._read_mode),
            raw,
            self._process(raw)  # <-- self._substituted can be changed here
        )
        self._substituted.insert(0, primary_seg)
        return self._substituted

    @property
    def char_class(self) -> CharClass:
        return self._char_class

    @property
    def label_stack(self) -> LabelPOV:
        return self._label_stack

    def _process(self, raw: bytes) -> str:
        return ''.join(self._process_byte(b) for b in raw)

    def _process_byte(self, b: int) -> str:
        return self._label_stack.get(self._display_mode, self._read_mode)

    def _create_primary_segment(self, opening_seq: SequenceSGR, raw: bytes, processed: str) -> Segment:
        return Segment(opening_seq, self._get_type_label(), raw, processed)

    def _create_details_segment(self, raw: bytes, processed: str) -> Segment:
        return Segment(self._get_details_opening_seq(), TYPE_LABEL_DETAILS, raw, processed)

    def _get_type_label(self) -> str:
        return TYPE_LABEL_MAP[self._char_class]

    def _get_details_opening_seq(self) -> SequenceSGR:
        raise NotImplemented

    @staticmethod
    def wrap_in_separators(s: str|List[Segment]) -> str|None:
        if isinstance(s, str):
            return f'{Template.SEPARATOR_LEFT}{s}{Template.SEPARATOR_RIGHT}'

        if isinstance(s, list):
            s.insert(0, Segment(seq.build_c256(255), '', b'', Template.SEPARATOR_LEFT))
            s.append(Segment(seq.build_c256(255), '', b'', Template.SEPARATOR_RIGHT))
            return

        raise TypeError(f'Invalid argument type {type(s)}')
