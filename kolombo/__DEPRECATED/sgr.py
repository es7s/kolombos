from pytermor import seq, autof
from pytermor.fmt import Format

from . import Marker
from ..settings import SettingsManager


class MarkerSGR(Marker):
    # even though we allow to colorize content, we'll explicitly disable any inversion and overline
    #  effect to guarantee that the only inversed and/or overlined things on the screen are our markers
    # also disable blinking
    PROHIBITED_CONTENT_BREAKER: SequenceSGR = seq.INVERSED_OFF + seq.OVERLINED_OFF + seq.BLINK_OFF

    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._initialized: bool = False
        self._marker_seq: SequenceSGR
        self._info_seq: SequenceSGR

    def print(self, additional_info: str = '', sgr: SequenceSGR = None):
        self._init_seqs()
        result = f'{seq.RESET}{self._marker_seq}{self._marker_char}'

        if SettingsManager.app_settings.no_color_markers:
            result += f'{additional_info}{sgr}'
        else:
            result += f'{sgr}{self._info_seq}{additional_info}'

        if SettingsManager.app_settings.effective_color_content:
            result += (self.PROHIBITED_CONTENT_BREAKER)  # ... content
        else:
            result += (seq.RESET)  # ... content
        return result

    def get_fmt(self) -> Format:
        self._init_seqs()
        return autof(self._marker_seq)

    def _init_seqs(self):
        if self._initialized:
            return

        self._marker_seq = seq.WHITE + seq.BG_BLACK
        if SettingsManager.app_settings.focus_esc:
            self._info_seq = seq.INVERSED
            if not SettingsManager.app_settings.no_color_markers:
                self._info_seq += seq.OVERLINED
        else:
            self._info_seq = seq.OVERLINED
        self._marker_seq += self._info_seq
        self._initialized = True
