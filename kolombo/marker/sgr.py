from pytermor import SequenceSGR, RESET, Format
from pytermor.preset import INVERSED_OFF, OVERLINED_OFF, BLINK_OFF, WHITE, BG_BLACK, INVERSED, OVERLINED

from . import Marker
from ..settings import Settings


class MarkerSGR(Marker):
    # even though we allow to colorize content, we'll explicitly disable any inversion and overline
    #  effect to guarantee that the only inversed and/or overlined things on the screen are our markers
    # also disable blinking
    PROHIBITED_CONTENT_SEQS: SequenceSGR = INVERSED_OFF + OVERLINED_OFF + BLINK_OFF

    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._initialized: bool = False
        self._marker_seq: SequenceSGR
        self._info_seq: SequenceSGR

    def print(self, additional_info: str = '', seq: SequenceSGR = None):
        self._init_seqs()
        result = f'{RESET}{self._marker_seq}{self._marker_char}'

        if Settings.no_color_markers:
            result += f'{additional_info}{seq}'
        else:
            result += f'{seq}{self.PROHIBITED_CONTENT_SEQS}' \
                      f'{self._info_seq}{additional_info}'

        if Settings.no_color_content:
            result += str(RESET)  # ... content
        else:
            result += str(self.PROHIBITED_CONTENT_SEQS)  # ... content
        return result

    def get_fmt(self) -> Format:
        self._init_seqs()
        return Format(self._marker_seq, reset=True)

    def _init_seqs(self):
        if self._initialized:
            return

        self._marker_seq = WHITE + BG_BLACK
        if Settings.focus_esc:
            self._info_seq = INVERSED
            if not Settings.no_color_markers:
                self._info_seq += OVERLINED
        else:
            self._info_seq = OVERLINED
        self._marker_seq += self._info_seq
        self._initialized = True
