from __future__ import annotations

from argparse import Namespace
from typing import Any

from pytermor import fmt, autof, seq

from kolombo.byteio.char_class import CharClass
from kolombo.byteio.display_mode import DisplayMode
from kolombo.byteio.read_mode import ReadMode


class SettingsEnum:
    MARKER_NO_DETAILS = 0
    MARKER_BRIEF_DETAILS = 1
    MARKER_FULL_DETAILS = 2
    MARKER_BINARY_STRICT = 3


class Settings(Namespace):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        # auto: bool = True
        self.binary: bool = False
        self.buffer: int|None = None  # auto
        self.columns: int|None = None  # auto
        self.decimal_offsets: bool = False
        self.debug: int = 0
        self.decode: bool = False
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
        self.legend: bool = False
        self.marker: int = 1
        self.max_bytes: int|None = None  # no limit
        self.max_lines: int|None = None  # no limit
        self.no_color_content: bool = False
        self.no_color_markers: bool = False
        self.no_line_numbers: bool = False
        self.no_offsets: bool = False
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
    def effective_color_content(self) -> bool:
        if self.binary:
            return False
        return not self.no_color_content

    @property
    def effective_marker_details(self) -> int:
        if self.binary:
            return SettingsEnum.MARKER_BINARY_STRICT

        eff = max(SettingsEnum.MARKER_NO_DETAILS, self.marker)
        return min(SettingsEnum.MARKER_FULL_DETAILS, eff)

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

    @staticmethod
    def debug_print_values():
        app_settings = SettingsManager.app_settings
        if not app_settings.debug_settings:
            return
        from kolombo.console import Console, ConsoleDebugBuffer

        def is_derived(attr: str, settings: Settings) -> bool:
            return attr not in settings.__dict__

        default_settings = Settings()
        debug_buffer = ConsoleDebugBuffer()
        fmt_header = autof(seq.BG_BLACK + seq.BOLD)

        attrs = [attr for attr in sorted(app_settings.__dir__(),
                                         key=lambda attr: attr if is_derived(attr, app_settings) else '_'+attr)
                 if not attr.startswith('_') and not attr.startswith('init')]
        if not app_settings.debug_settings_derived:
            attrs = list(filter(lambda attr: not is_derived(attr, app_settings), attrs))

        max_attr_len = max([len(attr) for attr in attrs]) + 3
        Console.settings_prefix_len = max_attr_len
        debug_buffer.write(3, Console.get_separator_line(settings_open=True))
        debug_buffer.write(3, fmt_header(f'Settings'.upper().ljust(max_attr_len)) + Console.get_separator())

        printed_derived_separator = False
        for attr in attrs:
            app_value = getattr(app_settings, attr)
            default_value = getattr(default_settings, attr)

            if app_value != default_value:
                fmt_attr_seq = fmt_header.opening_seq
                values = fmt.green(f'{app_value!s}') + ' ' + fmt.gray(f'[{default_value!s}]')
            else:
                fmt_attr_seq = seq.BG_BLACK
                values = fmt.yellow(f'{default_value!s}')

            if is_derived(attr, app_settings):
                fmt_attr_seq += seq.ITALIC
                if not printed_derived_separator:
                    debug_buffer.write(3, Console.get_separator_line(settings_mid=True))
                    debug_buffer.write(3,
                                       fmt_header(f'Derived settings'.upper().ljust(max_attr_len)) +
                                       Console.get_separator())
                    printed_derived_separator = True

            debug_buffer.write(3, autof(fmt_attr_seq)(attr.rjust(max_attr_len)) + Console.get_separator() + values)

        debug_buffer.write(3, Console.get_separator_line(settings_close=True, main_open=True))
