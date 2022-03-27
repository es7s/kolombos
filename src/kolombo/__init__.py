from argparse import Namespace
from typing import Optional


class Settings(Namespace):
    binary: bool
    filename: Optional[str]
    focus_control: bool
    focus_esc: bool
    focus_space: bool
    grid: bool
    ignore_control: bool
    ignore_esc: bool
    ignore_space: bool
    info: int
    legend: bool
    no_line_numbers: bool
    lines: int
    bytes: int
    no_color_content: bool
    no_color_marker: bool
    pipe_stderr: bool
    text: bool
    columns: int

    @staticmethod
    def effective_info_level() -> int:
        if Settings.binary:
            return 2
        return Settings.info
