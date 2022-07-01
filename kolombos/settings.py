# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from argparse import Namespace
from typing import Any

from .byteio import CharClass, DisplayMode, ReadMode, MarkerDetailsEnum


class Settings(Namespace):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        # auto: bool = True
        self.binary: bool = False
        self.buffer: int|None = None  # auto
        self.columns: int|None = None  # auto
        self.decimal_offsets: bool = False
        self.debug: int = 0
        self.decode: bool = False  # @TODO get rid of; will be useless after breakdown mode impl
        self.filename: str|None = None
        self.focus_control: bool = False
        self.focus_esc: bool = False
        self.focus_space: bool = False
        self.focus_utf8: bool = False
        self.focus_binary: bool = False
        self.focus_printable: bool = False
        self.ignore_control: bool = False
        self.ignore_esc: bool = False
        self.ignore_space: bool = False
        self.ignore_utf8: bool = False
        self.ignore_binary: bool = False
        self.ignore_printable: bool = False
        self.hide_ignored: bool = False  # TODO
        self.legend: bool = False
        self.marker: int = MarkerDetailsEnum.DEFAULT.value
        self.max_bytes: int|None = None  # no limit
        self.max_lines: int|None = None  # no limit
        self.no_color_markers: bool = False
        self.no_line_numbers: bool = False
        self.no_separators: bool = False
        self.no_offsets: bool = False
        self.squash_ignored: bool = False  # TODO
        self.text: bool = True
        self.version: bool = False

    @property
    def read_mode(self) -> ReadMode:
        if self.binary:
            return ReadMode.BINARY
        elif self.text:
            return ReadMode.TEXT
        # auto
        raise ValueError('Read mode is undefined')

    def get_char_class_display_mode(self, char_class: CharClass) -> DisplayMode:
        attr_ignored = f'ignore_{char_class.value}'
        attr_focused = f'focus_{char_class.value}'
        if not hasattr(self, attr_ignored):
            raise KeyError(f'Ignore attribute for char class {char_class} not found in settings (tried {attr_ignored})')
        if not hasattr(self, attr_focused):
            raise KeyError(f'Focus attribute for char class {char_class} not found in settings (tried {attr_focused})')

        if getattr(self, attr_ignored):
            return DisplayMode.IGNORED
        if getattr(self, attr_focused):
            return DisplayMode.FOCUSED
        return DisplayMode.DEFAULT

    @property
    def effective_marker_details(self) -> MarkerDetailsEnum:
        if self.binary:
            return MarkerDetailsEnum.BINARY_STRICT

        if self.marker <= 0:
            return MarkerDetailsEnum.NO_DETAILS
        if self.marker == 1:
            return MarkerDetailsEnum.BRIEF_DETAILS
        return MarkerDetailsEnum.FULL_DETAILS

    @property
    def effective_print_offsets(self) -> bool:
        if self.debug:
            return True
        return not self.no_offsets

    @property
    def debug_settings(self) -> int:
        return self.debug >= 3

    @property
    def debug_settings_derived(self) -> int:
        return self.debug >= 4

    @property
    def debug_buffer_contents(self) -> int:
        return self.debug >= 3

    @property
    def debug_buffer_contents_full(self) -> int:
        return self.debug >= 4


class SettingsManager:
    app_settings: Settings

    @staticmethod
    def init():
        SettingsManager.app_settings = Settings()
