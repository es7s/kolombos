from pytermor import build_c256, seq, autof

from .control_char import MarkerControlChar
from .escape_seq import MarkerEscapeSeq
from .ignored import MarkerIgnored
from .sgr import MarkerSGR
from .utf8 import MarkerUTF8
from .whitespace import MarkerWhitespace
from ..settings import SettingsManager


class MarkerRegistry:
    _unicode_control_marker_chars = ['ù', 'ú', 'û', 'ü', 'ũ', 'ŭ', 'ů', 'ű', 'ū']

    @staticmethod
    def get_control_marker(charcode: int):
        text_max_len = SettingsManager.app_settings.marker_details_max_len
        if charcode == 0x00:
            return MarkerControlChar('Ø', seq.HI_RED)
        elif charcode == 0x1b:  # standalone escape
            return MarkerControlChar('Ǝ', seq.HI_YELLOW)
        elif charcode == 0x08:
            return MarkerControlChar('←', seq.RED)
        elif charcode == 0x7f:
            return MarkerControlChar('→', seq.RED)
        elif 0x00 <= charcode < 0x20:
            marker_char = 'Ɐ'
            if text_max_len == 1:
                return MarkerControlChar(marker_char, seq.RED)
            return MarkerControlChar(marker_char + f'{charcode:x}'[-(text_max_len-1):], seq.RED)
        elif 0x80 <= charcode <= 0xfe:
            marker_char = MarkerRegistry._unicode_control_marker_chars[
                charcode % len(MarkerRegistry._unicode_control_marker_chars)
            ]
            return MarkerControlChar(f'{marker_char}{charcode:x}'[:text_max_len], seq.MAGENTA, no_focus=True)
        elif charcode == 0xff:
            return MarkerControlChar('◻', seq.HI_MAGENTA, no_focus=True)
        raise ValueError(f'Unknown control character code: "{charcode}"')

    @staticmethod
    def get_esq_marker(introducer_charcode: int):
        if 0x20 <= introducer_charcode < 0x30:
            return MarkerEscapeSeq('ꟻ', seq.GREEN)
        elif 0x30 <= introducer_charcode:
            return MarkerEscapeSeq('Ǝ', seq.YELLOW)
        raise ValueError(f'Unknown escape sequence introducer code: "{introducer_charcode}"')

    marker_ignored = MarkerIgnored('×', seq.BG_BLACK + seq.GRAY)
    marker_utf8 = MarkerUTF8('ṳ')  # ǚ

    marker_tab = MarkerWhitespace('⇥')
    marker_tab_keep_orig = MarkerWhitespace('⇥\t')
    marker_space = MarkerWhitespace('␣', '·')
    marker_newline = MarkerWhitespace('↵')
    marker_newline_keep_orig = MarkerWhitespace('↵\n')
    marker_vert_tab = MarkerWhitespace('⤓')
    marker_form_feed = MarkerWhitespace('↡')
    marker_car_return = MarkerWhitespace('⇤')

    marker_sgr_reset = MarkerSGRReset('ϴ')
    marker_sgr = MarkerSGR('ǝ')
    marker_esq_csi = MarkerEscapeSeq('Ͻ', seq.GREEN)

    fmt_first_chunk_col = autof(build_c256(231) + build_c256(238, bg=True))
    fmt_nth_row_col = autof(build_c256(231) + build_c256(238, bg=True) + seq.OVERLINED)
