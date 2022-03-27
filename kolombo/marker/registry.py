from pytermor import build_text256_seq, build_background256_seq
from pytermor.preset import *

from .control_char import MarkerControlChar
from .escape_seq import MarkerEscapeSeq
from .sgr import MarkerSGR
from .sgr_reset import MarkerSGRReset
from .whitespace import MarkerWhitespace


class MarkerRegistry:
    _tpl_marker_ascii_ctrl = MarkerControlChar('Ɐ{}', RED)

    @staticmethod
    def get_control_marker(charcode: int, text_max_len: int = 0):
        if charcode == 0x00:
            return MarkerControlChar('Ø', HI_RED)
        elif charcode == 0x1b:  # standalone escape
            return MarkerControlChar('Ǝ', HI_YELLOW)
        elif charcode == 0x08:
            return MarkerControlChar('←', RED)
        elif charcode == 0x7f:
            return MarkerControlChar('→', RED)
        elif 0x00 <= charcode < 0x20:
            return MarkerControlChar(f'Ɐ{charcode:x}'[:text_max_len], RED)
        elif 0x80 <= charcode <= 0xff:
            return MarkerControlChar(f'U{charcode:x}'[:text_max_len], MAGENTA)
        raise ValueError(f'Unknown control character code: "{charcode}"')

    @staticmethod
    def get_esq_marker(introducer_charcode: int):
        if 0x20 <= introducer_charcode < 0x30:
            return MarkerEscapeSeq('ꟻ', GREEN)
        elif 0x30 <= introducer_charcode:
            return MarkerEscapeSeq('Ǝ', YELLOW)
        raise ValueError(f'Unknown escape sequence introducer code: "{introducer_charcode}"')

    marker_tab = MarkerWhitespace('⇥\t')
    marker_space = MarkerWhitespace('␣', '·')
    marker_newline = MarkerWhitespace('↵')
    marker_vert_tab = MarkerWhitespace('⤓')
    marker_form_feed = MarkerWhitespace('↡')
    marker_car_return = MarkerWhitespace('⇤')

    marker_sgr_reset = MarkerSGRReset('ϴ')
    marker_sgr = MarkerSGR('ǝ')
    marker_esc_csi = MarkerEscapeSeq('Ͻ', GREEN)

    fmt_first_chunk_col = Format(build_text256_seq(231) + build_background256_seq(238), COLOR_OFF + BG_COLOR_OFF)
    fmt_nth_row_col = Format(build_text256_seq(231) + build_background256_seq(238) + OVERLINED,
                             COLOR_OFF + BG_COLOR_OFF + OVERLINED_OFF)
