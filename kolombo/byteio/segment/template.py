from __future__ import annotations

from copy import copy
from math import ceil

from pytermor import seq
from pytermor.seq import SequenceSGR, EmptySequenceSGR

from . import _opt_arg
from .segment import Segment
from ...settings import Settings


class SegmentTemplate:
    def __init__(self, label: str, type_label: str = '*', opening: SequenceSGR = None):
        self._label = label
        self._type_label = type_label
        self._opening: SequenceSGR = _opt_arg(opening)

    def __repr__(self):
        return f'{self.__class__.__name__}["{self._label}", "{self._type_label}", {self._opening!r}]'

    def default(self, span: bytes, ov_label: str | None = None, ov_type_label: str = None) -> Segment:
        if ov_type_label is None:
            ov_type_label = self._type_label
        if ov_label is None:
            ov_label = self._label * len(span)
        return Segment(span, ov_label, self._opening, ov_type_label)

    def ignore(self, span: bytes):
        return T_IGNORED.default(span, ov_type_label=self._type_label.lower())

    @property
    def label(self) -> str:
        return self._label

    @property
    def type_label(self) -> str:
        return self._type_label


class SegmentTemplateWhitespace(SegmentTemplate):
    def __init__(self,
                 label: str,
                 type_label: str = 'S',
                 opening: SequenceSGR = seq.DIM,
                 opening_focused: SequenceSGR = seq.BG_CYAN + seq.BLACK
                 ):
        super().__init__(label, type_label, opening=(opening_focused if Settings.focus_space else opening))


T_DEFAULT = SegmentTemplate('.', 'P')
T_IGNORED = SegmentTemplate('×', '', seq.BG_BLACK + seq.GRAY)
T_UTF8 = SegmentTemplate('ṳ', 'U', (seq.HI_BLUE + seq.INVERSED) if Settings.focus_utf8 else seq.HI_BLUE)  # ǚ
T_WHITESPACE = SegmentTemplateWhitespace('␣')
T_NEWLINE = SegmentTemplateWhitespace('↵')
T_NEWLINE_TEXT = SegmentTemplateWhitespace('↵\n')
T_CONTROL = SegmentTemplate('Ɐ', 'C', (seq.RED + seq.INVERSED) if Settings.focus_control else seq.RED)

# marker_tab = MarkerWhitespace('⇥')
# marker_tab_keep_orig = MarkerWhitespace('⇥\t')
# marker_space = MarkerWhitespace('␣', '·')
# marker_newline = MarkerWhitespace('↵')
# marker_newline_keep_orig = MarkerWhitespace('\n')
# marker_vert_tab = MarkerWhitespace('⤓')
# marker_form_feed = MarkerWhitespace('↡')
# marker_car_return = MarkerWhitespace('⇤')
#
# marker_sgr_reset = MarkerSGRReset('ϴ')
# marker_sgr = MarkerSGR('ǝ')
# marker_esq_csi = MarkerEscapeSeq('Ͻ', seq.GREEN)
#
# fmt_first_chunk_col = autof(build_c256(231) + build_c256(238, bg=True))
# fmt_nth_row_col = autof(build_c256(231) + build_c256(238, bg=True) + seq.OVERLINED)
