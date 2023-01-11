# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022-2023. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
Module contains definitions for low-level ANSI escape sequences building.
Can be used for creating a variety of sequences including:

    - :abbr:`SGR (Select Graphic Rendition)` sequences (text and background
      coloring, other text formatting and effects);
    - :abbr:`CSI (Control Sequence Introducer)` sequences (cursor management,
      selective screen cleraing);
    - :abbr:`OSC (Operating System Command)` sequences (varoius system commands).

.. important ::
    blah-blah-blah low-level @TODO

"""
from __future__ import annotations

from abc import abstractmethod, ABCMeta
from copy import copy
import enum
import typing as t

from .common import ConflictError


class ISequence(t.Sized, metaclass=ABCMeta):
    """
    Abstract ancestor of all escape sequences.
    """

    _ESC_CHARACTER: str = "\x1b"
    _SEPARATOR: str = ";"
    _INTRODUCER: str
    _TERMINATOR: str

    def __init__(self, *params: int | str):
        """
        :param  \*params:  Sequence internal parameters, existnce and
                           valid amount depends on sequence type.
        """
        self._params: t.List[int | str] = []

        for param in params:
            if isinstance(param, IntCode):
                self._params.append(
                    param.value
                )  # to avoid casting it later in assemble()
                continue
            self._params.append(param)

    def assemble(self) -> str:
        """
        Build up actual byte sequence and return
        as an ASCII-encoded string.
        """
        return (
            self._ESC_CHARACTER
            + self._INTRODUCER
            + self._SEPARATOR.join([str(param) for param in self.params])
            + self._TERMINATOR
        )

    @property
    def params(self) -> t.List[int | str]:
        """
        Return internal params as array.
        """
        return self._params

    @classmethod
    @abstractmethod
    def _short_class_name(cls):
        raise NotImplementedError

    def __str__(self) -> str:
        return self.assemble()

    def __len__(self) -> int:
        return 0

    def __eq__(self, other: ISequence):
        if type(self) != type(other):
            return False
        return self._params == other._params

    def __repr__(self) -> str:
        params = ",".join([str(p) for p in self._params])
        return f"<{self._short_class_name()}[{params}]>"


class ISequenceFe(ISequence, metaclass=ABCMeta):
    """
    Wide range of sequence types that includes `CSI <SequenceCSI>`,
    `OSC <SequenceOSC>` and more.

    All subtypes of this sequence start with ``ESC`` plus ASCII byte
    from ``0x40`` to ``0x5F`` (``@``, ``[``, ``\\``, ``]``, ``_``, ``^`` and
    capital letters ``A``-``Z``).
    """


class SequenceST(ISequenceFe):
    """
    String Terminator sequence (ST). Terminates strings in other control
    sequences. Encoded as ``ESC \\`` (``0x1B`` ``0x5C``).
    """

    _INTRODUCER = "\\"

    def assemble(self) -> str:
        return self._ESC_CHARACTER + self._INTRODUCER

    @classmethod
    def _short_class_name(cls) -> str:
        return "ST"


class SequenceOSC(ISequenceFe):
    """
    :abbr:`OSC (Operating System Command)`-type sequence. Starts a control
    string for the operating system to use. Encoded as ``ESC ]``, plus params
    separated by ``;``, and terminated with `SequenceST`.
    """

    _INTRODUCER = "]"
    _TERMINATOR = SequenceST().assemble()

    @classmethod
    def _short_class_name(cls):
        return "OSC"


class SequenceCSI(ISequenceFe):
    """
    Class representing :abbr:`CSI (Control Sequence Introducer)`-type ANSI
    escape sequence. All subtypes of this sequence start with ``ESC [``.

    Sequences of this type are used to control text formatting,
    change cursor position, erase screen and more.

    >>> make_erase_in_line().assemble()
    '\x1b[0K'

    """

    _INTRODUCER = "["

    def __init__(self, terminator: str, short_name: str, *params: int):
        """

        :param terminator:
        :param short_name:
        :param params:
        """
        self._terminator = terminator
        self._short_name = short_name
        super().__init__(*params)

    def regexp(self) -> str:
        return f"\\x1b\\[[0-9;]*{self._terminator}"

    def assemble(self) -> str:
        return (
            self._ESC_CHARACTER
            + self._INTRODUCER
            + self._SEPARATOR.join([str(param) for param in self.params])
            + self._terminator
        )

    def _short_class_name(self):
        result = "CSI"
        if self._short_name:
            result += ":" + self._short_name
        return result


class SequenceSGR(SequenceCSI):
    """
    Class representing :abbr:`SGR (Select Graphic Rendition)`-type escape sequence
    with varying amount of parameters. SGR sequences allow to change the color
    of text or/and terminal background (in 3 different color spaces) as well
    as set decorate text with italic style, underlining, overlining, cross-lining,
    making it bold or blinking etc.

    When cast to *str*, as all other sequences, invokes `assemble()` method
    and transforms into encoded control sequence string. It is possible to add
    of one SGR sequence to another, resulting in a new one with merged params
    (see examples).

    .. note ::
        `SequenceSGR` with zero params was specifically implemented to
        translate into empty string and not into ``ESC [m``, which would have
        made sense, but also would be entangling, as this sequence is the equivalent
        of ``ESC [0m`` -- hard reset sequence. The empty-string-sequence is
        predefined at module level as `NOOP_SEQ`.

    .. note ::
        The module doesn't distinguish "single-instruction" sequences from several
        ones merged together, e.g. ``Style(fg='red', bold=True)`` produces only one
        opening SequenceSGR instance:

        >>> SequenceSGR(IntCode.BOLD, IntCode.RED).assemble()
        '\x1b[1;31m'

        ...although generally speaking it is two of them (``ESC [1m`` and
        ``ESC [31m``). However, the module can automatically match terminating
        sequences for any form of input SGRs and translate it to specified format.

    >>> SequenceSGR(IntCode.HI_CYAN, 'underlined', 1)
    <SGR[96,4,1]>
    >>> SequenceSGR(31) + SequenceSGR(1) == SequenceSGR(31, 1)
    True

    :param args:  ..  ::

                    Sequence params. Resulting param order is the same as an
                    argument order. Each argument can be specified as:

                     - *str* -- any of `IntCode` names, case-insensitive
                     - *int* -- `IntCode` instance or plain integer
                     - `SequenceSGR` instance (params will be extracted)
    """

    _TERMINATOR = "m"

    def __init__(self, *args: str | int | SequenceSGR):
        result: t.List[int] = []

        for arg in args:
            if isinstance(arg, str):
                result.append(IntCode.resolve(arg).value)
            elif isinstance(arg, int):
                result.append(arg)
            elif isinstance(arg, SequenceSGR):
                result.extend(arg.params)
            else:
                raise TypeError(f"Invalid argument type: {arg!r})")

        result = [max(0, p) for p in result]
        super().__init__(self._TERMINATOR, "SGR", *result)

    def assemble(self) -> str:
        if len(self._params) == 0:  # NOOP
            return ""

        return (
            self._ESC_CHARACTER
            + self._INTRODUCER
            + self._SEPARATOR.join([str(param) for param in self._params])
            + self._TERMINATOR
        )

    @property
    def params(self) -> t.List[int]:
        """
        :return: Sequence params as integers or `IntCode` instances.
        """
        return super().params

    def __hash__(self) -> int:
        return int.from_bytes(self.assemble().encode(), byteorder="big")

    def __add__(self, other: SequenceSGR) -> SequenceSGR:
        self._ensure_sequence(other)
        return SequenceSGR(*self._params, *other._params)

    def __radd__(self, other: SequenceSGR) -> SequenceSGR:
        return other.__add__(self)

    def __iadd__(self, other: SequenceSGR) -> SequenceSGR:
        return self.__add__(other)

    def __eq__(self, other: SequenceSGR):
        if type(self) != type(other):
            return False
        return self._params == other._params

    @staticmethod
    def _ensure_sequence(subject: t.Any):
        if not isinstance(subject, SequenceSGR):
            raise TypeError(f"Expected SequenceSGR, got {type(subject)}")

    @staticmethod
    def validate_extended_color(value: int):
        if value < 0 or value > 255:
            raise ValueError(
                f"Invalid color value: expected range [0-255], got: {value}"
            )

    @classmethod
    def _short_class_name(cls) -> str:
        return "SGR"


# class UnderlinedCurlySequenceSGR(SequenceSGR):
#     """
#     Registered as a separate class, because this is the one and only SGR in the
#     package, which is identified by "4:3" string (in contrast with all the other
#     sequences entirely made of digits and semicolon separators).
#     """
#
#     def __init__(self):
#         """ """
#         super().__init__()
#         self._params = [f"{IntCode.UNDERLINED}:3"]
#
#     @property
#     def params(self) -> t.List[str]:
#         """ """
#         return self._params

class _NoOpSequenceSGR(SequenceSGR):
    def __init__(self):
        super().__init__()

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: SequenceSGR) -> bool:
        if not isinstance(other, SequenceSGR):
            return False
        return self._params == other._params

    def __repr__(self) -> str:
        return f"<{self._short_class_name()}[NOP]>"


NOOP_SEQ = _NoOpSequenceSGR()
"""
Special sequence in case you *have to* provide one or another SGR, but do 
not want any control sequences to be actually included in the output. 
``NOOP_SEQ.assemble()`` returns empty string, ``NOOP_SEQ.params`` 
returns empty list.

>>> NOOP_SEQ.assemble()
''
>>> NOOP_SEQ.params
[]

"""


class IntCode(enum.IntEnum):
    """
    Complete or almost complete list of reliably working SGR param integer codes.
    Fully interchangeable with plain *int*. Suitable for `SequenceSGR`
    default constructor.

    .. note ::
        `IntCode` predefined constants are omitted from documentation to avoid
        useless repeats and save space, as most of the time "next level" class
        `SeqIndex` is more appropriate, and on top of that, the constant
        names are literally the same for `SeqIndex` and `IntCode`.
    """

    @classmethod
    def resolve(cls, name: str) -> IntCode:
        """

        :param name:
        """
        name_norm = name.upper()
        try:
            instance = cls[name_norm]
        except KeyError as e:
            e.args = (f"Int code '{name_norm}' (<- '{name}') does not exist",)
            raise e
        return instance

    def __repr__(self) -> str:
        return f"<{self.value}|{self.name}>"

    # -- SGR: default attributes and colors -----------------------------------

    RESET = 0  # hard reset code
    BOLD = 1
    DIM = 2
    ITALIC = 3
    UNDERLINED = 4
    # CURLY_UNDERLINED = '4:3'  # TODO
    BLINK_SLOW = 5
    BLINK_FAST = 6
    INVERSED = 7
    HIDDEN = 8
    CROSSLINED = 9
    DOUBLE_UNDERLINED = 21
    OVERLINED = 53
    BOLD_DIM_OFF = 22  # no sequence to disable BOLD or DIM while keeping the other
    ITALIC_OFF = 23
    UNDERLINED_OFF = 24
    BLINK_OFF = 25
    INVERSED_OFF = 27
    HIDDEN_OFF = 28
    CROSSLINED_OFF = 29
    COLOR_OFF = 39
    BG_COLOR_OFF = 49
    OVERLINED_OFF = 55

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    COLOR_EXTENDED = 38

    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGENTA = 45
    BG_CYAN = 46
    BG_WHITE = 47
    BG_COLOR_EXTENDED = 48

    # UNDERLINE_COLOR_EXTENDED = 58  # @TODO
    # UNDERLINE_COLOR_OFF = 59

    GRAY = 90
    HI_RED = 91
    HI_GREEN = 92
    HI_YELLOW = 93
    HI_BLUE = 94
    HI_MAGENTA = 95
    HI_CYAN = 96
    HI_WHITE = 97

    BG_GRAY = 100
    BG_HI_RED = 101
    BG_HI_GREEN = 102
    BG_HI_YELLOW = 103
    BG_HI_BLUE = 104
    BG_HI_MAGENTA = 105
    BG_HI_CYAN = 106
    BG_HI_WHITE = 107

    # RARELY SUPPORTED (thus excluded)
    # 10-20: font selection
    #    26: proportional spacing
    #    50: disable proportional spacing
    #    51: framed
    #    52: encircled
    #    54: neither framed nor encircled
    # 60-65: ideogram attributes
    # 73-75: superscript and subscript

    # -- SGR: extended modifiers ----------------------------------------------

    EXTENDED_MODE_256 = 5
    EXTENDED_MODE_RGB = 2

    # -- Other sequence classes -----------------------------------------------

    HYPERLINK = 8


class SeqIndex:
    """
    Registry of static sequence presets.
    """

    # -- SGR ------------------------------------------------------------------

    RESET = SequenceSGR(IntCode.RESET)
    """
    Hard reset sequence.
    """

    BOLD = SequenceSGR(IntCode.BOLD)
    """ Bold or increased intensity. """

    DIM = SequenceSGR(IntCode.DIM)
    """ Faint, decreased intensity. """

    ITALIC = SequenceSGR(IntCode.ITALIC)
    """ Italic *(not widely supported)*. """

    UNDERLINED = SequenceSGR(IntCode.UNDERLINED)
    """ Underline. """

    BLINK_SLOW = SequenceSGR(IntCode.BLINK_SLOW)
    """ Set blinking to < 150 cpm. """

    BLINK_FAST = SequenceSGR(IntCode.BLINK_FAST)
    """ Set blinking to 150+ cpm *(not widely supported)*. """

    INVERSED = SequenceSGR(IntCode.INVERSED)
    """ Swap foreground and background colors. """

    HIDDEN = SequenceSGR(IntCode.HIDDEN)
    """ Conceal characters *(not widely supported)*. """

    CROSSLINED = SequenceSGR(IntCode.CROSSLINED)
    """ Strikethrough. """

    DOUBLE_UNDERLINED = SequenceSGR(IntCode.DOUBLE_UNDERLINED)
    """ Double-underline. *On several terminals disables* `BOLD` *instead*. """

    OVERLINED = SequenceSGR(IntCode.OVERLINED)
    """ Overline *(not widely supported)*. """

    BOLD_DIM_OFF = SequenceSGR(IntCode.BOLD_DIM_OFF)
    """
    Disable ``BOLD`` and ``DIM`` attributes.\n
    *Special aspects... It's impossible to reliably disable them on a separate basis.*
    """

    ITALIC_OFF = SequenceSGR(IntCode.ITALIC_OFF)
    """ Disable italic. """

    UNDERLINED_OFF = SequenceSGR(IntCode.UNDERLINED_OFF)
    """ Disable underlining. """

    BLINK_OFF = SequenceSGR(IntCode.BLINK_OFF)
    """ Disable blinking. """

    INVERSED_OFF = SequenceSGR(IntCode.INVERSED_OFF)
    """ Disable inversing. """

    HIDDEN_OFF = SequenceSGR(IntCode.HIDDEN_OFF)
    """ Disable conecaling. """

    CROSSLINED_OFF = SequenceSGR(IntCode.CROSSLINED_OFF)
    """ Disable strikethrough. """

    OVERLINED_OFF = SequenceSGR(IntCode.OVERLINED_OFF)
    """ Disable overlining. """

    # text colors

    BLACK = SequenceSGR(IntCode.BLACK)
    """ Set text color to 0x000000. """

    RED = SequenceSGR(IntCode.RED)
    """ Set text color to 0x800000. """

    GREEN = SequenceSGR(IntCode.GREEN)
    """ Set text color to 0x008000. """

    YELLOW = SequenceSGR(IntCode.YELLOW)
    """ Set text color to 0x808000. """

    BLUE = SequenceSGR(IntCode.BLUE)
    """ Set text color to 0x000080. """

    MAGENTA = SequenceSGR(IntCode.MAGENTA)
    """ Set text color to 0x800080. """

    CYAN = SequenceSGR(IntCode.CYAN)
    """ Set text color to 0x008080. """

    WHITE = SequenceSGR(IntCode.WHITE)
    """ Set text color to 0xc0c0c0. """

    COLOR_OFF = SequenceSGR(IntCode.COLOR_OFF)
    """ Reset foreground color. """

    # background colors

    BG_BLACK = SequenceSGR(IntCode.BG_BLACK)
    """ Set background color to 0x000000. """

    BG_RED = SequenceSGR(IntCode.BG_RED)
    """ Set background color to 0x800000. """

    BG_GREEN = SequenceSGR(IntCode.BG_GREEN)
    """ Set background color to 0x008000. """

    BG_YELLOW = SequenceSGR(IntCode.BG_YELLOW)
    """ Set background color to 0x808000. """

    BG_BLUE = SequenceSGR(IntCode.BG_BLUE)
    """ Set background color to 0x000080. """

    BG_MAGENTA = SequenceSGR(IntCode.BG_MAGENTA)
    """ Set background color to 0x800080. """

    BG_CYAN = SequenceSGR(IntCode.BG_CYAN)
    """ Set background color to 0x008080. """

    BG_WHITE = SequenceSGR(IntCode.BG_WHITE)
    """ Set background color to 0xc0c0c0. """

    BG_COLOR_OFF = SequenceSGR(IntCode.BG_COLOR_OFF)
    """ Reset background color. """

    # high intensity text colors

    GRAY = SequenceSGR(IntCode.GRAY)
    """ Set text color to 0x808080. """
    HI_RED = SequenceSGR(IntCode.HI_RED)
    """ Set text color to 0xff0000. """
    HI_GREEN = SequenceSGR(IntCode.HI_GREEN)
    """ Set text color to 0x00ff00. """
    HI_YELLOW = SequenceSGR(IntCode.HI_YELLOW)
    """ Set text color to 0xffff00. """
    HI_BLUE = SequenceSGR(IntCode.HI_BLUE)
    """ Set text color to 0x0000ff. """
    HI_MAGENTA = SequenceSGR(IntCode.HI_MAGENTA)
    """ Set text color to 0xff00ff. """
    HI_CYAN = SequenceSGR(IntCode.HI_CYAN)
    """ Set text color to 0x00ffff. """
    HI_WHITE = SequenceSGR(IntCode.HI_WHITE)
    """ Set text color to 0xffffff. """

    # high intensity background colors

    BG_GRAY = SequenceSGR(IntCode.BG_GRAY)
    """ Set background color to 0x808080. """
    BG_HI_RED = SequenceSGR(IntCode.BG_HI_RED)
    """ Set background color to 0xff0000. """
    BG_HI_GREEN = SequenceSGR(IntCode.BG_HI_GREEN)
    """ Set background color to 0x00ff00. """
    BG_HI_YELLOW = SequenceSGR(IntCode.BG_HI_YELLOW)
    """ Set background color to 0xffff00. """
    BG_HI_BLUE = SequenceSGR(IntCode.BG_HI_BLUE)
    """ Set background color to 0x0000ff. """
    BG_HI_MAGENTA = SequenceSGR(IntCode.BG_HI_MAGENTA)
    """ Set background color to 0xff00ff. """
    BG_HI_CYAN = SequenceSGR(IntCode.BG_HI_CYAN)
    """ Set background color to 0x00ffff. """
    BG_HI_WHITE = SequenceSGR(IntCode.BG_HI_WHITE)
    """ Set background color to 0xffffff. """

    # -- OSC ------------------------------------------------------------------

    HYPERLINK = SequenceOSC(IntCode.HYPERLINK)
    """
    Create a hyperlink in the text *(supported by limited amount of terminals)*.
    Note that for a working hyperlink you'll need two sequences, not just one.
     
    .. seealso ::
        `make_hyperlink_part()` and `assemble_hyperlink()`.
    """


COLORS = list(range(30, 39))
BG_COLORS = list(range(40, 49))
HI_COLORS = list(range(90, 98))
BG_HI_COLORS = list(range(100, 108))
ALL_COLORS = COLORS + BG_COLORS + HI_COLORS + BG_HI_COLORS


class _SgrPairityRegistry:
    """
    Internal class providing methods for mapping SGRs to a
    complement (closing) SGRs, also referred to as "resetters".
    """

    _code_to_resetter_map: t.Dict[int | t.Tuple[int, ...], SequenceSGR] = dict()
    _complex_code_def: t.Dict[int | t.Tuple[int, ...], int] = dict()
    _complex_code_max_len: int = 0

    def __init__(self):
        _regulars = [
            (IntCode.BOLD, IntCode.BOLD_DIM_OFF),
            (IntCode.DIM, IntCode.BOLD_DIM_OFF),
            (IntCode.ITALIC, IntCode.ITALIC_OFF),
            (IntCode.UNDERLINED, IntCode.UNDERLINED_OFF),
            (IntCode.DOUBLE_UNDERLINED, IntCode.UNDERLINED_OFF),
            (IntCode.BLINK_SLOW, IntCode.BLINK_OFF),
            (IntCode.BLINK_FAST, IntCode.BLINK_OFF),
            (IntCode.INVERSED, IntCode.INVERSED_OFF),
            (IntCode.HIDDEN, IntCode.HIDDEN_OFF),
            (IntCode.CROSSLINED, IntCode.CROSSLINED_OFF),
            (IntCode.OVERLINED, IntCode.OVERLINED_OFF),
        ]

        for c in _regulars:
            self._bind_regular(*c)

        for c in [*COLORS, *HI_COLORS]:
            self._bind_regular(c, IntCode.COLOR_OFF)

        for c in [*BG_COLORS, *BG_HI_COLORS]:
            self._bind_regular(c, IntCode.BG_COLOR_OFF)

        self._bind_complex((IntCode.COLOR_EXTENDED, 5), 1, IntCode.COLOR_OFF)
        self._bind_complex((IntCode.COLOR_EXTENDED, 2), 3, IntCode.COLOR_OFF)
        self._bind_complex((IntCode.BG_COLOR_EXTENDED, 5), 1, IntCode.BG_COLOR_OFF)
        self._bind_complex((IntCode.BG_COLOR_EXTENDED, 2), 3, IntCode.BG_COLOR_OFF)

    def _bind_regular(self, starter_code: int | t.Tuple[int, ...], resetter_code: int):
        if starter_code in self._code_to_resetter_map:
            raise ConflictError(f"SGR {starter_code} already has a registered resetter")

        self._code_to_resetter_map[starter_code] = SequenceSGR(resetter_code)

    def _bind_complex(
        self, starter_codes: t.Tuple[int, ...], param_len: int, resetter_code: int
    ):
        self._bind_regular(starter_codes, resetter_code)

        if starter_codes in self._complex_code_def:
            raise ConflictError(f"SGR {starter_codes} already has a registered resetter")

        self._complex_code_def[starter_codes] = param_len
        self._complex_code_max_len = max(
            self._complex_code_max_len, len(starter_codes) + param_len
        )

    def get_closing_seq(self, opening_seq: SequenceSGR) -> SequenceSGR:
        closing_seq_params: t.List[int] = []
        opening_params = copy(opening_seq.params)

        while len(opening_params):
            key_params: int | t.Tuple[int, ...] | None = None

            for complex_len in range(
                1, min(len(opening_params), self._complex_code_max_len + 1)
            ):
                opening_complex_suggestion = tuple(opening_params[:complex_len])

                if opening_complex_suggestion in self._complex_code_def:
                    key_params = opening_complex_suggestion
                    complex_total_len = (
                        complex_len + self._complex_code_def[opening_complex_suggestion]
                    )
                    opening_params = opening_params[complex_total_len:]
                    break

            if key_params is None:
                key_params = opening_params.pop(0)
            if key_params not in self._code_to_resetter_map:
                continue

            closing_seq_params.extend(self._code_to_resetter_map[key_params].params)

        return SequenceSGR(*closing_seq_params)


_sgr_pairity_registry = _SgrPairityRegistry()


def get_closing_seq(opening_seq: SequenceSGR) -> SequenceSGR:
    """

    :param opening_seq:
    :return:
    """
    return _sgr_pairity_registry.get_closing_seq(opening_seq)


def enclose(opening_seq: SequenceSGR, string: str) -> str:
    """

    :param opening_seq:
    :param string:
    :return:
    """
    return f"{opening_seq}{string}{get_closing_seq(opening_seq)}"


def make_set_cursor_x_abs(x: int = 1) -> SequenceCSI:
    """
    Create :abbr:`CHA (Cursor Horizontal Absolute)` sequence that sets
    cursor horizontal position, or column, to ``x``.

    :param x:  New cursor horizontal position.
    :example:  ``ESC [1G``
    """
    if x <= 0:
        raise ValueError(f"Invalid x value: {x}, expected x > 0")
    return SequenceCSI("G", "CHA", x)


def make_erase_in_line(mode: int = 0) -> SequenceCSI:
    """
    Create :abbr:`EL (Erase in Line)` sequence that erases a part of the line
    or the entire line. Cursor position does not change.

    :param mode:  .. ::

                  Sequence operating mode.

                     - If set to 0, clear from cursor to the end of the line.
                     - If set to 1, clear from cursor to beginning of the line.
                     - If set to 2, clear the entire line.

    :example:     ``ESC [0K``
    """
    if not (0 <= mode <= 2):
        raise ValueError(f"Invalid mode: {mode}, expected [0;2]")
    return SequenceCSI("K", "EL", mode)


def make_query_cursor_position() -> SequenceCSI:
    """
    Create :abbr:`QCP (Query Cursor Position)` sequence that requests an output
    device to respond with a structure containing current cursor coordinates
    (`RCP <decompose_request_cursor_position()>`).

    .. warning ::

        Sending this sequence to the terminal may **block** infinitely. Consider
        using a thread or set a timeout for the main thread using a signal.

    :example:   ``ESC [6n``
    """

    return SequenceCSI("n", "QCP", 6)


def decompose_request_cursor_position(string: str) -> t.Tuple[int, int]|None:
    """
    Parse :abbr:`RCP (Report Cursor Position)` sequence that generally comes from
    a terminal as a response to `QCP <make_query_cursor_position>` sequence and
    contains a cursor's current row and column.

    .. note ::

        As the library in general provides sequence assembling methods, but not
        the disassembling ones, there is no dedicated class for RCP sequences yet.

    >>> decompose_request_cursor_position('\x1b[18;2R')
    (18, 2)

    :param string:  Terminal response with a sequence.
    :return:        Current row and column if the expected sequence exists
                    in ``string``, *None* otherwise.
    """
    if not all(c in string for c in "\x1b[;R"):
        return None  # input does not contain a valid RCP sequence

    start_idx = string.rfind("\x1b[")
    seq = string[start_idx + 2: string.rfind("R") - start_idx]
    y, x = seq.split(";", 2)

    try:
        return int(y), int(x)
    except ValueError:
        return None  # unexpected results


def make_color_256(code: int, bg: bool = False) -> SequenceSGR:
    """
    Wrapper for creation of `SequenceSGR` that sets foreground
    (or background) to one of 256-color palette value.

    :param code:  Index of the color in the palette, 0 -- 255.
    :param bg:    Set to *True* to change the background color
                  (default is foreground).
    :example:     ``ESC [38;5;141m``
    """

    SequenceSGR.validate_extended_color(code)
    key_code = IntCode.BG_COLOR_EXTENDED if bg else IntCode.COLOR_EXTENDED
    return SequenceSGR(key_code, IntCode.EXTENDED_MODE_256, code)


def make_color_rgb(r: int, g: int, b: int, bg: bool = False) -> SequenceSGR:
    """
    Wrapper for creation of `SequenceSGR` operating in True Color mode (16M).
    Valid values for ``r``, ``g`` and ``b`` are in range of [0; 255]. This range
    linearly translates into [0x00; 0xFF] for each channel. The result
    value is composed as "0xRRGGBB". For example, sequence with color of
    0xFF3300 can be created with::

        make_color_rgb(255, 51, 0)

    :param r:  Red channel value, 0 -- 255.
    :param g:  Blue channel value, 0 -- 255.
    :param b:  Green channel value, 0 -- 255.
    :param bg: Set to *True* to change the background color (default is foreground).
    :example:  ``ESC [38;2;255;51;0m``
    """

    [SequenceSGR.validate_extended_color(color) for color in [r, g, b]]
    key_code = IntCode.BG_COLOR_EXTENDED if bg else IntCode.COLOR_EXTENDED
    return SequenceSGR(key_code, IntCode.EXTENDED_MODE_RGB, r, g, b)


def make_hyperlink_part(url: str = None) -> SequenceOSC:
    """

    :param url:
    :example: ``ESC ]8;;http://localhost ESC \\``
    """
    return SequenceOSC(IntCode.HYPERLINK, "", (url or ""))


def assemble_hyperlink(url: str, label: str = None) -> str:
    """

    :param url:
    :param label:
    :example:  ``ESC ]8;;http://localhost ESC \\Text ESC ]8;; ESC \\``
    """
    return f"{make_hyperlink_part(url)}{label or url}{make_hyperlink_part()}"
