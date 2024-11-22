# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import List

from pytermor import SequenceSGR, Seqs, ansi

from .. import CharClass, DisplayMode, MarkerDetailsEnum, ReadMode, PartialOverride, OpeningSeqPOV, LabelPOV
from ..const import TYPE_LABEL_MAP, TYPE_LABEL_DETAILS
from ..segment import Segment
from ...settings import SettingsManager


@dataclass(frozen=True)
class Separators(Iterable):
    left: str
    right: str

    def __iter__(self):
        yield self.left
        yield self.right


class Template:
    SEPARATOR_MAP: dict[str|None, Separators] = {  # @TODO keys to enum?
        None: Separators('⢸', '⡇'),
        "alt": Separators('｣', '｢'),
    }

    IGNORED_LABEL: str = '×'
    IGNORED_OPENING_SEQ: SequenceSGR = Seqs.GRAY + Seqs.DIM
    DETAILS_OPENING_SEQ: SequenceSGR = SequenceSGR.init_color_indexed(16, True) + Seqs.UNDERLINED

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
        self._separators: Separators = self._get_separators_default()

        if not self._opening_seq_stack.has_key(DisplayMode.FOCUSED):
            self._opening_seq_stack.set(DisplayMode.FOCUSED, self._opening_seq_stack.get() + Seqs.INVERSED)
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
        self._decode = app_settings.decode if isinstance(app_settings.decode, bool) else False
        if app_settings.alt_separators:
            self._separators = self.SEPARATOR_MAP.get('alt')

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

    @classmethod
    def _get_separators_default(cls) -> Separators:
        return cls.SEPARATOR_MAP.get(None)

    @classmethod
    def _get_separators_alt(cls) -> Separators:
        return cls.SEPARATOR_MAP.get('alt')

    @staticmethod
    def _wrap_in_separators(separators: Separators, s: str|List[Segment]) -> str|None:
        if isinstance(s, str):
            return s.join(separators)

        if isinstance(s, list):
            s.insert(0, Segment(SequenceSGR.init_color_indexed(255), '', b'',  separators.left))
            s.append(Segment(SequenceSGR.init_color_indexed(255), '', b'', separators.right))
            return  # @FIXME WTF modifying a list which is provided to the method by value (copy)??

        raise TypeError(f'Invalid argument type {type(s)}')

    @staticmethod
    def wrap_in_default_separators(s: str|List[Segment]) -> str|None:
        return Template._wrap_in_separators(Template._get_separators_default(), s)

    @staticmethod
    def wrap_in_alt_separators(s: str|List[Segment]) -> str|None:
        return Template._wrap_in_separators(Template._get_separators_alt(), s)

    def _wrap_in_configured_separators(self, s: str|List[Segment]) -> str|None:
        return self._wrap_in_separators(self._separators, s)
