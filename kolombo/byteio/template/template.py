from __future__ import annotations

from pytermor import seq
from pytermor.seq import SequenceSGR

from . import PartialOverride, OpeningSeqPOV, LabelPOV
from .. import CharClass, DisplayMode, ReadMode
from ..enum import TYPE_LABEL_MAP
from ..segment import Segment
from ...settings import SettingsManager


class Template:
    IGNORED_OPENING_SEQ: SequenceSGR = seq.GRAY + seq.DIM
    IGNORED_LABEL: str = '×'

    def __init__(self, char_class: CharClass, opening_seq: SequenceSGR | OpeningSeqPOV, label: str | LabelPOV = ''):
        if not isinstance(opening_seq, PartialOverride):
            opening_seq = OpeningSeqPOV(opening_seq)
        if not isinstance(label, PartialOverride):
            label = LabelPOV(label)

        self._char_class: CharClass = char_class
        self._opening_seq_stack: OpeningSeqPOV = opening_seq
        self._label_stack: LabelPOV = label

        if not self._opening_seq_stack.has_key(DisplayMode.FOCUSED):
            self._opening_seq_stack.set(DisplayMode.FOCUSED, self._opening_seq_stack.get() + seq.INVERSED)
        if not self._opening_seq_stack.has_key(DisplayMode.IGNORED):
            self._opening_seq_stack.set(DisplayMode.IGNORED, self.IGNORED_OPENING_SEQ)

        if not self._label_stack.has_key(DisplayMode.IGNORED):
            self._label_stack.set(DisplayMode.IGNORED, self.IGNORED_LABEL)

    def substitute(self, raw: bytes) -> Segment:
        app_settings = SettingsManager.app_settings
        display_mode = app_settings.get_char_class_display_mode(self._char_class)
        read_mode = app_settings.read_mode

        return Segment(
            self._opening_seq_stack.get(display_mode, read_mode),  # display_mode has more priority
            TYPE_LABEL_MAP[self._char_class],
            raw,
            self._process(raw, display_mode, read_mode)
        )

    def _process(self, raw: bytes, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        processed = ''
        for b in raw:
            processed += self._process_byte(b, display_mode, read_mode)
        return processed

    def _process_byte(self, b: int, display_mode: DisplayMode, read_mode: ReadMode) -> str:
        return self._label_stack.get(display_mode, read_mode)  # display_mode has more priority

# CharClass.ESCAPE_SEQ     'E' ! GN|Y|WH|vari  marker:byte-dep: 'ϴǝϽꟻƎ' | +seq.INVERSED marker:byte-dep:content-dep:'ϴǝϽꟻƎ' | const.IGNORED | binary invisible
# content-dep:: ^^^^^^^^^^
#
# opening <-- raw, display_mode
# label <-- read_mode, raw, marker, decode, display_mode