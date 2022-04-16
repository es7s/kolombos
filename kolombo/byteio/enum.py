from enum import Enum
from typing import Dict


class ReadMode(Enum):
    TEXT = 'text'
    BINARY = 'binary'


class DisplayMode(Enum):
    DEFAULT = 'default'
    FOCUSED = 'focused'
    IGNORED = 'ignored'


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


class MarkerDetailsEnum(Enum):
    NO_DETAILS = 'no_details'
    BRIEF_DETAILS = 'brief_details'
    FULL_DETAILS = 'full_details'
    BINARY_STRICT = 'binary_strict'
