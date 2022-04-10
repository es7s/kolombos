from argparse import Namespace
from typing import Optional


class Settings(Namespace):
    # auto: bool
    binary: bool
    buffer: int
    columns: int
    debug: int
    debug_buffer_contents = bool
    debug_buffer_contents_full = bool
    decimal_offsets = bool
    decode: bool
    filename: Optional[str]
    focus_control: bool
    focus_esc: bool
    focus_space: bool
    focus_utf8: bool
    ignore_control: bool
    ignore_esc: bool
    ignore_space: bool
    ignore_utf8: bool
    info: int
    legend: bool
    max_bytes: int
    max_lines: int
    no_color_content: bool
    no_color_markers: bool
    no_line_numbers: bool
    text: bool
    version: bool

    @staticmethod
    def init_set_defaults():
        # if not any([Settings.text, Settings.binary]):
        #     Settings.auto = True
        Settings.debug_buffer_contents = (Settings.debug >= 3)
        Settings.debug_buffer_contents_full = (Settings.debug >= 4)

    @staticmethod
    def effective_color_content() -> bool:
        if Settings.binary:
            return False
        return not Settings.no_color_content

    @staticmethod
    def effective_info_level() -> int:
        if Settings.binary:
            return 2
        return Settings.info

    @staticmethod
    def control_marker_max_len() -> int:
        if Settings.binary:
            return 1
        return Settings.info + 1
