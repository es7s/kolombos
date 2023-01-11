# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
Module contains definitions for low-level ANSI escape sequences handling.

The key difference beetween ``Spans`` and ``Sequences`` is that sequence can
*open* text style and also *close*, or terminate it. As for ``Spans`` -- they
always do both; typical use-case of `Span` is to wrap some text in opening SGR
and closing one.

Each variable in `Seqs` and `Spans` below is a valid argument
for :class:`.Span` and :class:`.SequenceSGR` default constructors; furthermore,
it can be passed in a string form (case-insensitive):

.. testsetup:: *

    from pytermor.ansi import SequenceSGR, Spans, Span, Seqs, IntCodes, NOOP_SPAN, NOOP_SEQ

>>> Span('BG_GREEN')
Span[SGR[42], SGR[49]]

>>> Span(Seqs.BG_GREEN, Seqs.UNDERLINED)
Span[SGR[42;4], SGR[49;24]]

"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from copy import copy
from typing import List, Any, Dict, Tuple, Sized

from .common import Registry


class Sequence(Sized, metaclass=ABCMeta):
    """
    Abstract ancestor of all escape sequences.
    """
    def __init__(self, *params: int):
        self._params: List[int] = [max(0, int(p)) for p in params]

    @abstractmethod
    def assemble(self) -> str:
        """
        Build up actual byte sequence and return
        as an ASCII-encoded string.
        """
        raise NotImplementedError

    @property
    def params(self) -> List[int]:
        """ Return internal params as array. """
        return self._params

    @classmethod
    @abstractmethod
    def _short_class_name(cls): raise NotImplementedError

    def __str__(self) -> str:
        return self.assemble()

    def __len__(self) -> int:
        return 0

    def __eq__(self, other: Sequence):
        if type(self) != type(other):
            return False
        return self._params == other._params

    def __repr__(self):
        params = ";".join([str(p) for p in self._params])
        if len(self._params) == 0:
            params = '~'
        return f'{self._short_class_name()}[{params}]'


class SequenceCSI(Sequence, metaclass=ABCMeta):
    """
    Abstract class representing CSI-type ANSI escape sequence. All subtypes
    of this sequence start with :kbd:`\\e[`.
    """
    _CONTROL_CHARACTER = '\x1b'
    _INTRODUCER = '['
    _SEPARATOR = ';'

    def __init__(self, *params: int):
        super(SequenceCSI, self).__init__(*params)

    @classmethod
    def regexp(cls) -> str:
        return f'\\x1b\\[[0-9;]*{cls._terminator()}'

    @classmethod
    @abstractmethod
    def _terminator(cls) -> str: raise NotImplementedError


class SequenceSGR(SequenceCSI, metaclass=ABCMeta):
    """
    Class representing SGR-type escape sequence with varying amount of parameters.

    `SequenceSGR` with zero params was specifically implemented to
    translate into empty string and not into :kbd:`\\e[m`, which would have
    made sense, but also would be very entangling, as this sequence is
    equivalent of :kbd:`\\e[0m` -- hard reset sequence. The empty-string-sequence
    is predefined as `NOOP_SEQ`.

    It's possible to add of one SGR sequence to another:

    >>> SequenceSGR(31) + SequenceSGR(1) == SequenceSGR(31, 1)
    True

    """
    _TERMINATOR = 'm'

    def __init__(self, *args: str|int|SequenceSGR):
        """
        Create new `SequenceSGR` with specified ``args`` as params.

        Resulting sequence param order is same as an argument order.

        Each sequence param can be specified as:
          - string key (name of any constant defined in `IntCodes`, case-insensitive)
          - integer param value (``IntCodes`` values)
          - existing ``SequenceSGR`` instance (params will be extracted).

        >>> SequenceSGR('yellow', 'bold')
        SGR[33;1]
        >>> SequenceSGR(91, 7)
        SGR[91;7]
        >>> SequenceSGR(IntCodes.HI_CYAN, IntCodes.UNDERLINED)
        SGR[96;4]
        """
        result: List[int] = []

        for arg in args:
            if isinstance(arg, str):
                resolved_param = IntCodes.resolve(arg)
                if not isinstance(resolved_param, int):
                    raise ValueError(f'Attribute is not valid SGR param: {resolved_param}')
                result.append(resolved_param)
            elif isinstance(arg, int):
                result.append(arg)
            elif isinstance(arg, SequenceSGR):
                result.extend(arg.params)
            else:
                raise TypeError(f'Invalid argument type: {arg!r})')

        super().__init__(*result)

    @classmethod
    def init_color_indexed(cls, idx: int, bg: bool = False) -> SequenceSGR:
        """
        Wrapper for creation of `SequenceSGR` that sets foreground
        (or background) to one of 256-color pallete value.

        :param idx:  Index of the color in the pallete, 0 -- 255.
        :param bg:    Set to *True* to change the background color
                      (default is foreground).
        :return:      `SequenceSGR` with required params.
        """

        cls._validate_extended_color(idx)
        key_code = IntCodes.BG_COLOR_EXTENDED if bg else IntCodes.COLOR_EXTENDED
        return SequenceSGR(key_code, IntCodes.EXTENDED_MODE_256, idx)

    @classmethod
    def init_color_rgb(cls, r: int, g: int, b: int, bg: bool = False) -> SequenceSGR:
        """
        Wrapper for creation of `SequenceSGR` operating in True Color mode (16M).
        Valid values for *r*, *g* and *b* are in range [0; 255]. This range
        linearly translates into [``0x00``; ``0xFF``] for each channel. The result
        value is composed as ``#RRGGBB``. For example, sequence with color of
        ``#FF3300`` can be created with::

            SequenceSGR.init_color_rgb(255, 51, 0)

        :param r:  Red channel value, 0 -- 255.
        :param g:  Blue channel value, 0 -- 255.
        :param b:  Green channel value, 0 -- 255.
        :param bg: Set to *True* to change the background color
                   (default is foreground).
        :return:   `SequenceSGR` with required params.
        """

        [cls._validate_extended_color(color) for color in [r, g, b]]
        key_code = IntCodes.BG_COLOR_EXTENDED if bg else IntCodes.COLOR_EXTENDED
        return SequenceSGR(key_code, IntCodes.EXTENDED_MODE_RGB, r, g, b)

    def assemble(self) -> str:
        if len(self._params) == 0:  # NOOP
            return ''

        params = self._params
        if params == [0]:  # \x1b[0m <=> \x1b[m, saving 1 byte
            params = []

        return (self._CONTROL_CHARACTER +
                self._INTRODUCER +
                self._SEPARATOR.join([str(param) for param in params]) +
                self._TERMINATOR)

    def __hash__(self) -> int:
        return int.from_bytes(self.assemble().encode(), byteorder='big')

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

    @property
    def is_color_extended(self) -> bool:
        return len(self.params) >= 3 and \
               (self.params[0] == IntCodes.COLOR_EXTENDED or
                self.params[0] == IntCodes.BG_COLOR_EXTENDED)

    @staticmethod
    def _ensure_sequence(subject: Any):
        if not isinstance(subject, SequenceSGR):
            raise TypeError(f'Expected SequenceSGR, got {type(subject)}')

    @staticmethod
    def _validate_extended_color(value: int):
        if value < 0 or value > 255:
            raise ValueError(
                f'Invalid color value: expected range [0-255], got: {value}')

    @classmethod
    def _terminator(cls) -> str:
        return cls._TERMINATOR

    @classmethod
    def _short_class_name(cls) -> str:
        return 'SGR'


# noinspection PyMethodMayBeStatic
class Span:
    """
    Class consisting of two `SequenceSGR` instances -- the first one, "opener",
    tells the terminal that's it should format subsequent characters as specified,
    and the second one, which reverses the effects of the  first one.
    """
    def __init__(self, *opening_params: str|int|SequenceSGR):
        """
        Create a `Span` with specified control sequence(s) as an opening sequence
        and **automatically compose** second (closing) sequence that will terminate
        attributes defined in the first one while keeping the others (*soft* reset).

        Resulting sequence param order is same as an argument order.

        Each argument can be specified as:
          - string key (name of any constant defined in `IntCodes`, case-insensitive)
          - integer param value (``IntCodes`` values)
          - existing `SequenceSGR` instance (params will be extracted).

        >>> Span('red', 'bold')
        Span[SGR[31;1], SGR[39;22]]
        >>> Span(IntCodes.GREEN)
        Span[SGR[32], SGR[39]]
        >>> Span(93, 4)
        Span[SGR[93;4], SGR[39;24]]
        >>> Span(Seqs.BG_BLACK + Seqs.RED)
        Span[SGR[40;31], SGR[49;39]]

        :param opening_params: string keys, integer codes or existing ``SequenceSGR``
                               instances to build ``Span`` from.
        """
        self._opening_seq = SequenceSGR(*opening_params)
        if len(opening_params) == 0:
            self._closing_seq = SequenceSGR()
            return

        self._closing_seq = _SgrPairityRegistry.get_closing_seq(self._opening_seq)

    @classmethod
    def init_explicit(cls, opening_seq: SequenceSGR = None,
                      closing_seq: SequenceSGR = None,
                      hard_reset_after: bool = False) -> Span:
        """
        Create new `Span` with explicitly specified opening and closing sequences.

        .. note ::
            `closing_seq` gets overwritten with `Seqs.RESET` if ``hard_reset_after`` is *True*.

        :param opening_seq:      Starter sequence, in general determening how `Span` will actually look like.
        :param closing_seq:      Finisher SGR sequence.
        :param hard_reset_after: Terminate *all* formatting after this span.
        """
        instance = Span()
        instance._opening_seq = cls._opt_arg(opening_seq)
        instance._closing_seq = cls._opt_arg(closing_seq)

        if hard_reset_after:
            instance._closing_seq = Seqs.RESET

        return instance

    def wrap(self, text: Any = None) -> str:
        """
        Wrap given ``text`` string with ``SGRs`` defined on initialization -- `opening_seq`
        on the left, `closing_seq` on the right. ``str(text)`` will
        be invoked for all argument types with the exception of *None*,
        which will be replaced with an empty string.

        :param text:  String to wrap.
        :return:      ``text`` enclosed in instance's ``SGRs``, if any.
        """
        result = self._opening_seq.assemble()

        if text is not None:
            result += str(text)

        result += self._closing_seq.assemble()
        return result

    @property
    def opening_str(self) -> str:
        """ Return opening SGR sequence assembled. """
        return self._opening_seq.assemble()

    @property
    def opening_seq(self) -> 'SequenceSGR':
        """ Return opening SGR sequence instance. """
        return self._opening_seq

    @property
    def closing_str(self) -> str:
        """ Return closing SGR sequence assembled. """
        return self._closing_seq.assemble()

    @property
    def closing_seq(self) -> 'SequenceSGR':
        """ Return closing SGR sequence instance. """
        return self._closing_seq

    @classmethod
    def _opt_arg(self, arg: SequenceSGR | None) -> SequenceSGR:
        if not arg:
            return NOOP_SEQ
        return arg

    def __call__(self, text: Any = None) -> str:
        """
        Can be used instead of `wrap()` method.

        >>> Spans.RED('text') == Spans.RED.wrap('text')
        True
        """
        return self.wrap(text)

    def __eq__(self, other: Span) -> bool:
        if not isinstance(other, Span):
            return False
        return self._opening_seq == other._opening_seq and self._closing_seq == other._closing_seq

    def __repr__(self):
        return self.__class__.__name__ + '[{!r}, {!r}]'.format(self._opening_seq, self._closing_seq)


NOOP_SEQ = SequenceSGR()
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

NOOP_SPAN = Span()
"""
Special `Span` in cases where you *have to* select one or 
another `Span`, but do not want any control sequence to be actually included. 

- ``NOOP_SPAN(string)`` or ``NOOP_SPAN.wrap(string)`` returns ``string`` without any modifications;
- ``NOOP_SPAN.opening_str`` and ``NOOP_SPAN.closing_str`` are empty strings;
- ``NOOP_SPAN.opening_seq`` and ``NOOP_SPAN.closing_seq`` both returns `NOOP_SEQ`.

>>> NOOP_SPAN('text')
'text'
>>> NOOP_SPAN.opening_str
''
>>> NOOP_SPAN.opening_seq
SGR[~]
"""


class IntCodes(Registry[int]):
    """
    Complete or almost complete list of reliably working SGR param integer codes.

    Suitable for :class:`.Span` and :class:`.SequenceSGR` default constructors.

    .. attention::
       Registry constants are omitted from API doc pages to improve readability
       and avoid duplication. Summary list of all presets can be found in
       `guide.presets` section of the guide.
    """
    # -- Default attributes and colors --------------------------------------------

    RESET = 0  # hard reset code
    BOLD = 1
    DIM = 2
    ITALIC = 3
    UNDERLINED = 4
    BLINK_SLOW = 5
    BLINK_FAST = 6
    INVERSED = 7
    HIDDEN = 8
    CROSSLINED = 9
    DOUBLE_UNDERLINED = 21
    OVERLINED = 53
    BOLD_DIM_OFF = 22  # there is no separate sequence for disabling either
    ITALIC_OFF = 23               # of BOLD or DIM while keeping the other
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
    COLOR_EXTENDED = 38  # use init_color_indexed() and init_color_rgb() instead

    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGENTA = 45
    BG_CYAN = 46
    BG_WHITE = 47
    BG_COLOR_EXTENDED = 48  # use color_indexed() and color_rgb() instead

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
    # 58-59: underline color
    # 60-65: ideogram attributes
    # 73-75: superscript and subscript

    # -- Default colors lists -----------------------------------------------------

    LIST_COLORS = list(range(30, 39))
    LIST_BG_COLORS = list(range(40, 49))
    LIST_HI_COLORS = list(range(90, 98))
    LIST_BG_HI_COLORS = list(range(100, 108))

    LIST_ALL_COLORS = LIST_COLORS + LIST_BG_COLORS + \
                      LIST_HI_COLORS + LIST_BG_HI_COLORS

    # -- EXTENDED modifiers -------------------------------------------------------

    EXTENDED_MODE_256 = 5
    EXTENDED_MODE_RGB = 2


class Seqs(Registry[SequenceSGR]):
    """
    Registry of sequence presets.

    .. attention::
       Registry constants are omitted from API doc pages to improve readability
       and avoid duplication. Summary list of all presets can be found in
       `guide.presets` section of the guide.
    """

    RESET = SequenceSGR(IntCodes.RESET)
    """
    Hard reset sequence.
    """

    # attributes
    BOLD = SequenceSGR(IntCodes.BOLD)
    DIM = SequenceSGR(IntCodes.DIM)
    ITALIC = SequenceSGR(IntCodes.ITALIC)
    UNDERLINED = SequenceSGR(IntCodes.UNDERLINED)
    BLINK_SLOW = SequenceSGR(IntCodes.BLINK_SLOW)
    BLINK_FAST = SequenceSGR(IntCodes.BLINK_FAST)
    BLINK_DEFAULT = BLINK_SLOW
    INVERSED = SequenceSGR(IntCodes.INVERSED)
    HIDDEN = SequenceSGR(IntCodes.HIDDEN)
    CROSSLINED = SequenceSGR(IntCodes.CROSSLINED)
    DOUBLE_UNDERLINED = SequenceSGR(IntCodes.DOUBLE_UNDERLINED)
    OVERLINED = SequenceSGR(IntCodes.OVERLINED)

    BOLD_DIM_OFF = SequenceSGR(IntCodes.BOLD_DIM_OFF)       # there is no separate sequence for
    ITALIC_OFF = SequenceSGR(IntCodes.ITALIC_OFF)           # disabling either of BOLD or DIM
    UNDERLINED_OFF = SequenceSGR(IntCodes.UNDERLINED_OFF)   # while keeping the other
    BLINK_OFF = SequenceSGR(IntCodes.BLINK_OFF)
    INVERSED_OFF = SequenceSGR(IntCodes.INVERSED_OFF)
    HIDDEN_OFF = SequenceSGR(IntCodes.HIDDEN_OFF)
    CROSSLINED_OFF = SequenceSGR(IntCodes.CROSSLINED_OFF)
    OVERLINED_OFF = SequenceSGR(IntCodes.OVERLINED_OFF)

    # text colors
    BLACK = SequenceSGR(IntCodes.BLACK)
    RED = SequenceSGR(IntCodes.RED)
    GREEN = SequenceSGR(IntCodes.GREEN)
    YELLOW = SequenceSGR(IntCodes.YELLOW)
    BLUE = SequenceSGR(IntCodes.BLUE)
    MAGENTA = SequenceSGR(IntCodes.MAGENTA)
    CYAN = SequenceSGR(IntCodes.CYAN)
    WHITE = SequenceSGR(IntCodes.WHITE)
    # code.COLOR_EXTENDED is handled by color_indexed()
    COLOR_OFF = SequenceSGR(IntCodes.COLOR_OFF)

    # background colors
    BG_BLACK = SequenceSGR(IntCodes.BG_BLACK)
    BG_RED = SequenceSGR(IntCodes.BG_RED)
    BG_GREEN = SequenceSGR(IntCodes.BG_GREEN)
    BG_YELLOW = SequenceSGR(IntCodes.BG_YELLOW)
    BG_BLUE = SequenceSGR(IntCodes.BG_BLUE)
    BG_MAGENTA = SequenceSGR(IntCodes.BG_MAGENTA)
    BG_CYAN = SequenceSGR(IntCodes.BG_CYAN)
    BG_WHITE = SequenceSGR(IntCodes.BG_WHITE)
    # code.BG_COLOR_EXTENDED is handled by color_indexed()
    BG_COLOR_OFF = SequenceSGR(IntCodes.BG_COLOR_OFF)

    # high intensity text colors
    GRAY = SequenceSGR(IntCodes.GRAY)
    HI_RED = SequenceSGR(IntCodes.HI_RED)
    HI_GREEN = SequenceSGR(IntCodes.HI_GREEN)
    HI_YELLOW = SequenceSGR(IntCodes.HI_YELLOW)
    HI_BLUE = SequenceSGR(IntCodes.HI_BLUE)
    HI_MAGENTA = SequenceSGR(IntCodes.HI_MAGENTA)
    HI_CYAN = SequenceSGR(IntCodes.HI_CYAN)
    HI_WHITE = SequenceSGR(IntCodes.HI_WHITE)

    # high intensity background colors
    BG_GRAY = SequenceSGR(IntCodes.BG_GRAY)
    BG_HI_RED = SequenceSGR(IntCodes.BG_HI_RED)
    BG_HI_GREEN = SequenceSGR(IntCodes.BG_HI_GREEN)
    BG_HI_YELLOW = SequenceSGR(IntCodes.BG_HI_YELLOW)
    BG_HI_BLUE = SequenceSGR(IntCodes.BG_HI_BLUE)
    BG_HI_MAGENTA = SequenceSGR(IntCodes.BG_HI_MAGENTA)
    BG_HI_CYAN = SequenceSGR(IntCodes.BG_HI_CYAN)
    BG_HI_WHITE = SequenceSGR(IntCodes.BG_HI_WHITE)


class _SgrPairityRegistry:
    """
    Internal class responsible for correct SGRs termination.
    """
    _code_to_breaker_map: Dict[int|Tuple[int, ...], SequenceSGR] = dict()
    _complex_code_def: Dict[int|Tuple[int, ...], int] = dict()
    _complex_code_max_len: int = 0

    @classmethod
    def __new__(cls, *args, **kwargs):

        _regulars = [(IntCodes.BOLD, IntCodes.BOLD_DIM_OFF),
                     (IntCodes.DIM, IntCodes.BOLD_DIM_OFF),
                     (IntCodes.ITALIC, IntCodes.ITALIC_OFF),
                     (IntCodes.UNDERLINED, IntCodes.UNDERLINED_OFF),
                     (IntCodes.DOUBLE_UNDERLINED, IntCodes.UNDERLINED_OFF),
                     (IntCodes.BLINK_SLOW, IntCodes.BLINK_OFF),
                     (IntCodes.BLINK_FAST, IntCodes.BLINK_OFF),
                     (IntCodes.INVERSED, IntCodes.INVERSED_OFF),
                     (IntCodes.HIDDEN, IntCodes.HIDDEN_OFF),
                     (IntCodes.CROSSLINED, IntCodes.CROSSLINED_OFF),
                     (IntCodes.OVERLINED, IntCodes.OVERLINED_OFF), ]

        for c in _regulars:
            cls.bind_regular(*c)

        for c in [*IntCodes.LIST_COLORS, *IntCodes.LIST_HI_COLORS]:
            cls.bind_regular(c, IntCodes.COLOR_OFF)

        for c in [*IntCodes.LIST_BG_COLORS, *IntCodes.LIST_BG_HI_COLORS]:
            cls.bind_regular(c, IntCodes.BG_COLOR_OFF)

        cls.bind_complex((IntCodes.COLOR_EXTENDED, 5), 1, IntCodes.COLOR_OFF)
        cls.bind_complex((IntCodes.COLOR_EXTENDED, 2), 3, IntCodes.COLOR_OFF)
        cls.bind_complex((IntCodes.BG_COLOR_EXTENDED, 5), 1, IntCodes.BG_COLOR_OFF)
        cls.bind_complex((IntCodes.BG_COLOR_EXTENDED, 2), 3, IntCodes.BG_COLOR_OFF)

    @classmethod
    def bind_regular(cls, starter_code: int|Tuple[int, ...], breaker_code: int):
        if starter_code in cls._code_to_breaker_map:
            raise RuntimeError(f'Conflict: SGR code {starter_code} already '
                               f'has a registered breaker')

        cls._code_to_breaker_map[starter_code] = SequenceSGR(breaker_code)

    @classmethod
    def bind_complex(cls, starter_codes: Tuple[int, ...], param_len: int,
                     breaker_code: int):
        cls.bind_regular(starter_codes, breaker_code)

        if starter_codes in cls._complex_code_def:
            raise RuntimeError(f'Conflict: SGR complex {starter_codes} already '
                               f'has a registered breaker')

        cls._complex_code_def[starter_codes] = param_len
        cls._complex_code_max_len = max(cls._complex_code_max_len,
                                         len(starter_codes) + param_len)

    @classmethod
    def get_closing_seq(cls, opening_seq: SequenceSGR) -> SequenceSGR:
        closing_seq_params: List[int] = []
        opening_params = copy(opening_seq.params)

        while len(opening_params):
            key_params: int|Tuple[int, ...]|None = None

            for complex_len in range(1, min(len(opening_params),
                                            cls._complex_code_max_len + 1)):
                opening_complex_suggestion = tuple(opening_params[:complex_len])

                if opening_complex_suggestion in cls._complex_code_def:
                    key_params = opening_complex_suggestion
                    complex_total_len = (
                        complex_len + cls._complex_code_def[opening_complex_suggestion])
                    opening_params = opening_params[complex_total_len:]
                    break

            if key_params is None:
                key_params = opening_params.pop(0)
            if key_params not in cls._code_to_breaker_map:
                continue

            closing_seq_params.extend(cls._code_to_breaker_map[key_params].params)

        return SequenceSGR(*closing_seq_params)

_SgrPairityRegistry()


class Spans(Registry[Span]):
    """
    Registry of span presets.

    .. attention::
       Registry constants are omitted from API doc pages to improve readability
       and avoid duplication. Summary list of all presets can be found in
       `guide.presets` section of the guide.
    """

    BOLD = Span(IntCodes.BOLD)
    DIM = Span(IntCodes.DIM)
    ITALIC = Span(IntCodes.ITALIC)
    UNDERLINED = Span(IntCodes.UNDERLINED)
    BLINK_SLOW = Span(IntCodes.BLINK_SLOW)
    BLINK_FAST = Span(IntCodes.BLINK_FAST)
    INVERSED = Span(IntCodes.INVERSED)
    HIDDEN = Span(IntCodes.HIDDEN)
    CROSSLINED = Span(IntCodes.CROSSLINED)
    DOUBLE_UNDERLINED = Span(IntCodes.DOUBLE_UNDERLINED)
    OVERLINED = Span(IntCodes.OVERLINED)

    BLACK = Span(IntCodes.BLACK)
    RED = Span(IntCodes.RED)
    GREEN = Span(IntCodes.GREEN)
    YELLOW = Span(IntCodes.YELLOW)
    BLUE = Span(IntCodes.BLUE)
    MAGENTA = Span(IntCodes.MAGENTA)
    CYAN = Span(IntCodes.CYAN)
    WHITE = Span(IntCodes.WHITE)

    GRAY = Span(IntCodes.GRAY)
    HI_RED = Span(IntCodes.HI_RED)
    HI_GREEN = Span(IntCodes.HI_GREEN)
    HI_YELLOW = Span(IntCodes.HI_YELLOW)
    HI_BLUE = Span(IntCodes.HI_BLUE)
    HI_MAGENTA = Span(IntCodes.HI_MAGENTA)
    HI_CYAN = Span(IntCodes.HI_CYAN)
    HI_WHITE = Span(IntCodes.HI_WHITE)

    BG_BLACK = Span(IntCodes.BG_BLACK)
    BG_RED = Span(IntCodes.BG_RED)
    BG_GREEN = Span(IntCodes.BG_GREEN)
    BG_YELLOW = Span(IntCodes.BG_YELLOW)
    BG_BLUE = Span(IntCodes.BG_BLUE)
    BG_MAGENTA = Span(IntCodes.BG_MAGENTA)
    BG_CYAN = Span(IntCodes.BG_CYAN)
    BG_WHITE = Span(IntCodes.BG_WHITE)

    BG_GRAY = Span(IntCodes.BG_GRAY)
    BG_HI_RED = Span(IntCodes.BG_HI_RED)
    BG_HI_GREEN = Span(IntCodes.BG_HI_GREEN)
    BG_HI_YELLOW = Span(IntCodes.BG_HI_YELLOW)
    BG_HI_BLUE = Span(IntCodes.BG_HI_BLUE)
    BG_HI_MAGENTA = Span(IntCodes.BG_HI_MAGENTA)
    BG_HI_CYAN = Span(IntCodes.BG_HI_CYAN)
    BG_HI_WHITE = Span(IntCodes.BG_HI_WHITE)
