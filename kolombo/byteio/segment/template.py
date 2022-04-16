from __future__ import annotations

from pytermor import seq
from pytermor.seq import SequenceSGR, EmptySequenceSGR, AbstractSequenceSGR

from kolombo.settings import SettingsManager


# noinspection PyMethodMayBeStatic
class SegmentTemplate:
    def __init__(self, label: str, type_label: str = '*', opening: AbstractSequenceSGR = None):
        self._label = label
        self._type_label = type_label
        self._opening: SequenceSGR = self._opt_opening_arg(opening)

    def __repr__(self):
        return '{}["{}", "{}", {!r}]'.format(
            self.__class__.__name__,
            self._label,
            self._type_label,
            self._opening)

    def substitute(self, raw: bytes, processed: str = None):
        from .segment import Segment
        if processed is None:
            processed = self._label * len(raw)
        return Segment(self._opening, self._type_label, raw, processed)

    @property
    def label(self) -> str:
        return self._label

    @property
    def type_label(self) -> str:
        return self._type_label

    @property
    def opening(self) -> SequenceSGR:
        return self._opening

    def _opt_opening_arg(self, arg: SequenceSGR|None) -> SequenceSGR|None:
        if isinstance(arg, SequenceSGR):
            return arg
        return EmptySequenceSGR()


class SegmentTemplateWhitespace(SegmentTemplate):
    def __init__(self, label: str, type_label: str = 'S'):
        opening = seq.GRAY # seq.DIM
        opening_focused = seq.BG_CYAN + seq.BLACK
        super().__init__(label, type_label, opening=(opening_focused if SettingsManager.app_settings.focus_space else opening))


T_PRINTABLE = SegmentTemplate('.', 'P', seq.INVERSED if SettingsManager.app_settings.focus_printable else None)
T_IGNORED = SegmentTemplate('×', '', seq.GRAY)
# binary mode -> ▯ :
T_UTF8 = SegmentTemplate('▯', 'U', (seq.HI_BLUE + seq.INVERSED) if SettingsManager.app_settings.focus_utf8 else seq.HI_BLUE)  # ǚṳ
T_BINARY = SegmentTemplate('▯', 'B', (seq.MAGENTA + seq.INVERSED) if SettingsManager.app_settings.focus_binary else seq.MAGENTA)
T_WHITESPACE = SegmentTemplateWhitespace('␣')
T_NEWLINE = SegmentTemplateWhitespace('↵')
T_NEWLINE_TEXT = SegmentTemplateWhitespace('↵\n')
# binary mode -> ▯ :
T_CONTROL = SegmentTemplate('Ɐ', 'C', (seq.RED + seq.INVERSED) if SettingsManager.app_settings.focus_control else seq.RED)
T_TEMP = SegmentTemplate('▯', '?', seq.HI_YELLOW + seq.BG_RED)

#  marker_tab = MarkerWhitespace('⇥')
# # marker_tab_keep_orig = MarkerWhitespace('⇥\t')
# # marker_space = MarkerWhitespace('␣', '·')
# # marker_newline = MarkerWhitespace('↵')
# # marker_newline_keep_orig = MarkerWhitespace('\n')
# # marker_vert_tab = MarkerWhitespace('⤓')
# # marker_form_feed = MarkerWhitespace('↡')
# # marker_car_return = MarkerWhitespace('⇤')
# #
# # marker_sgr_reset = MarkerSGRReset('ϴ')
# # marker_sgr = MarkerSGR('ǝ')
# # marker_esq_csi = MarkerEscapeSeq('Ͻ', seq.GREEN)
# #
# # fmt_first_chunk_col = autof(build_c256(231) + build_c256(238, bg=True))
# # fmt_nth_row_col = autof(build_c256(231) + build_c256(238, bg=True) + seq.OVERLINED)

