from __future__ import annotations

from copy import copy
from math import ceil

from pytermor import seq
from pytermor.seq import SequenceSGR, EmptySequenceSGR

from . import _opt_arg
from .segment import Segment


class SegmentTemplate:
    def __init__(self, label: str, opening: SequenceSGR = None, opening_focused: SequenceSGR = None, type_label: str = '*'):
        self._label = label
        self._open_sgr: SequenceSGR = _opt_arg(opening)
        self._open_focus_sgr: SequenceSGR|None = _opt_arg(opening_focused, allow_none=True)
        self._type_label = type_label

    def __repr__(self):
        return f'{self.__class__.__name__}["{self._label}", {self._open_sgr!r}, {self._open_focus_sgr!r}]'

    def __call__(self, span: bytes, label: str | None = None, focused: bool = False, type_label: str = None) -> Segment:
        open_sgr = self._open_sgr
        if focused:
            open_sgr = self._open_focus_sgr
            if open_sgr is None or isinstance(open_sgr, EmptySequenceSGR):
                raise Warning(f'Substituting with focused open SGR which is empty ({self!r})')

        if type_label is None:
            type_label = self._type_label

        if label is not None:
            return Segment(span, label, open_sgr, type_label)

        req_len = len(span)
        if req_len <= len(self._label):
            label = self._label[:req_len]
        else:
            label = self._label * ceil(req_len / len(self._label))
        return Segment(span, label, open_sgr, type_label)

    @property
    def type_label(self) -> str: return self._type_label


class SegmentTemplateWhitespace(SegmentTemplate):
    def __init__(self, label: str, opening: SequenceSGR = seq.DIM,
                 opening_focused: SequenceSGR = seq.BG_CYAN + seq.BLACK,
                 type_label: str = 'S'):
        super().__init__(label, opening=opening, opening_focused=opening_focused, type_label=type_label)


T_DEFAULT = SegmentTemplate('.', type_label='P')
T_IGNORED = SegmentTemplate('×', seq.BG_BLACK + seq.GRAY)
T_UTF8 = SegmentTemplate('ṳ', seq.HI_BLUE, seq.HI_BLUE + seq.INVERSED, type_label='U')  # ǚ
T_WHITESPACE = SegmentTemplateWhitespace('␣')
T_NEWLINE = SegmentTemplateWhitespace('↵')
T_CONTROL = SegmentTemplate('Ɐ', seq.DIM, seq.BG_CYAN + seq.BLACK, type_label='C')

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
