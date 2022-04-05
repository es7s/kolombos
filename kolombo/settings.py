from argparse import Namespace
from typing import Optional


class Settings(Namespace):
    auto: bool
    binary: bool
    buffer: int
    columns: int
    debug: int
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
    pipe_stderr: bool
    text: bool

    @staticmethod
    def set_defaults():
        if not any([Settings.text, Settings.binary]):
            Settings.auto = True

        if Settings.debug > 0 and (Settings.auto or Settings.text):
            Settings.auto = False
            Settings.binary = True
            Settings.text = False

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
