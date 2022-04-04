from argparse import Namespace
from typing import Optional


class Settings(Namespace):
    binary: bool
    filename: Optional[str]
    focus_control: bool
    focus_esc: bool
    focus_space: bool
    focus_utf8: bool
    grid: bool
    ignore_control: bool
    ignore_esc: bool
    ignore_space: bool
    ignore_utf8: bool
    info: int
    legend: bool
    no_line_numbers: bool
    lines: int
    bytes: int
    no_color_content: bool
    no_color_markers: bool
    pipe_stderr: bool
    text: bool
    columns: int
    decode: bool

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
