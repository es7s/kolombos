from __future__ import annotations

from pytermor import seq
from pytermor.seq import SequenceSGR

from . import _opt_arg
from ...settings import Settings


class SegmentTemplateSample:
    def __init__(self, tpl: SegmentTemplate, processed: str = None):
        self._template = tpl
        self._processed = processed

    @property
    def template(self) -> SegmentTemplate:
        return self._template

    def get_processed(self, len: int) -> str:
        if self._processed is None:
            self._processed = self._template.label * len
        return self._processed


class SegmentTemplate:
    def __init__(self, label: str, type_label: str = '*', opening: SequenceSGR = None):
        self._label = label
        self._type_label = type_label
        self._opening: SequenceSGR = _opt_arg(opening)

    def __repr__(self):
        return '{}["{}", "{}", {!r}]'.format(
            self.__class__.__name__,
            self._label,
            self._type_label,
            self._opening
    )

    def sample(self, processed: str = None) -> SegmentTemplateSample:
        return SegmentTemplateSample(self, processed)

    @property
    def label(self) -> str:
        return self._label

    @property
    def type_label(self) -> str:
        return self._type_label

    @property
    def opening(self) -> SequenceSGR:
        return self._opening


class SegmentTemplateWhitespace(SegmentTemplate):
    def __init__(self, label: str, type_label: str = 'S'):
        opening = seq.DIM
        opening_focused = seq.BG_CYAN + seq.BLACK
        super().__init__(label, type_label, opening=(opening_focused if Settings.focus_space else opening))


T_DEFAULT = SegmentTemplate('.', 'P')
T_IGNORED = SegmentTemplate('×', '', seq.GRAY)
T_UTF8 = SegmentTemplate('ṳ', 'U', (seq.HI_BLUE + seq.INVERSED) if Settings.focus_utf8 else seq.HI_BLUE)  # ǚ
T_WHITESPACE = SegmentTemplateWhitespace('␣')
T_NEWLINE = SegmentTemplateWhitespace('↵')
T_NEWLINE_TEXT = SegmentTemplateWhitespace('↵\n')
T_CONTROL = SegmentTemplate('Ɐ', 'C', (seq.RED + seq.INVERSED) if Settings.focus_control else seq.RED)
T_TEMP = SegmentTemplate('?', '?', seq.MAGENTA)

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
