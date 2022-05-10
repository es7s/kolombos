# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from enum import Enum
from typing import Dict, Union

CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]
PRINTABLE_CHARCODES = list(range(0x21, 0x7f))
BINARY_CHARCODES = list(range(0x80, 0x100))
CHARCODE_TO_SAFE_CHAR_MAP = {   # @TODO впилить в отладчоный вывод AbstractFormatter._seg_raw_to_safe
    **{b: chr(b) for b in range(0x00, 0x100)},
    **{b: '·' for b in WHITESPACE_CHARCODES},
    **{b: '▯' for b in CONTROL_CHARCODES},
    **{b: '▯' for b in BINARY_CHARCODES},
}


class ReadMode(Enum):
    BINARY = 'binary'
    TEXT = 'text'

    @property
    def is_binary(self) -> bool: return self is self.BINARY
    @property
    def is_text(self) -> bool: return self is self.TEXT


class DisplayMode(Enum):
    DEFAULT = 'default'
    FOCUSED = 'focused'
    IGNORED = 'ignored'

    @property
    def is_default(self) -> bool: return self is self.DEFAULT
    @property
    def is_focused(self) -> bool: return self is self.FOCUSED
    @property
    def is_ignored(self) -> bool: return self is self.IGNORED


ByteIOMode = Union[DisplayMode, ReadMode]


class CharClass(Enum):
    CONTROL_CHAR = 'control'
    ESCAPE_SEQ = 'esc'
    WHITESPACE = 'space'
    UTF_8_SEQ = 'utf8'
    BINARY_DATA = 'binary'
    PRINTABLE_CHAR = 'printable'


TYPE_LABEL_MAP: Dict[CharClass, str] = {
    CharClass.CONTROL_CHAR: 'C',
    CharClass.ESCAPE_SEQ: 'E',
    CharClass.WHITESPACE: 'S',
    CharClass.UTF_8_SEQ: 'U',
    CharClass.BINARY_DATA: 'B',
    CharClass.PRINTABLE_CHAR: 'P',
}
TYPE_LABEL_DETAILS = '*'


class MarkerDetailsEnum(Enum):
    NO_DETAILS = 0
    BRIEF_DETAILS = 1
    FULL_DETAILS = 2
    BINARY_STRICT = 3  # require len(raw) = len(processed)
    DEFAULT = BRIEF_DETAILS
