# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022-2023. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
Package containing a set of formatters for prettier output, as well as utility classes
for removing some of the boilerplate code when dealing with escape sequences. Also
includes several Python Standard Library methods rewritten for correct work with
strings containing control sequences.
"""
from __future__ import annotations

import codecs
import math
import os
import re
import textwrap
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from functools import reduce
from math import ceil
from typing import Union

from .common import ArgTypeError, Align
from .utilmisc import chunk, get_terminal_width

_PRIVATE_REPLACER = "\U000E5750"


def pad(n: int) -> str:
    return " " * n


def padv(n: int) -> str:
    return "\n" * n


def ljust_sgr(s: str, width: int, fillchar: str = " ", actual_len: int = None) -> str:
    """
    SGR-formatting-aware implementation of ``str.ljust``.

    Return a left-justified string of length ``width``. Padding is done
    using the specified fill character (default is a space).
    """
    if actual_len is None:
        actual_len = len(SgrStringReplacer().apply(s))
    return s + fillchar * max(0, width - actual_len)


def rjust_sgr(s: str, width: int, fillchar: str = " ", actual_len: int = None) -> str:
    """
    SGR-formatting-aware implementation of ``str.rjust``.

    Return a right-justified string of length ``width``. Padding is done
    using the specified fill character (default is a space).
    """
    if actual_len is None:
        actual_len = len(SgrStringReplacer().apply(s))
    return fillchar * max(0, width - actual_len) + s


def center_sgr(s: str, width: int, fillchar: str = " ", actual_len: int = None) -> str:
    """
    SGR-formatting-aware implementation of ``str.center``.

    Return a centered string of length ``width``. Padding is done using the
    specified fill character (default is a space).

    .. todo ::

        поверить корректность работы в случае эмодзи (напр. 🔋)
        если алгоритм поедет -- можно заменить на f-стринги
    """
    if actual_len is None:
        actual_len = len(SgrStringReplacer().apply(s))

    fill_len = max(0, width - actual_len)
    if fill_len == 0:
        return s

    if actual_len % 2 == 1:
        right_fill_len = math.ceil(fill_len / 2)
    else:
        right_fill_len = math.floor(fill_len / 2)
    left_fill_len = fill_len - right_fill_len
    return (fillchar * left_fill_len) + s + (fillchar * right_fill_len)


def wrap_sgr(
    raw_input: str | list[str], width: int, indent_first: int = 0, indent_subseq: int = 0
) -> str:
    """
    A workaround to make standard library ``textwrap.wrap()`` more friendly
    to an SGR-formatted strings.

    The main idea is

    :param raw_input:
    :param width:
    """
    # initially was written as a part of es7s/core
    # package, and transferred here later
    sgrs: list[str] = []

    def push(m: t.Match):
        sgrs.append(m.group())
        return _PRIVATE_REPLACER

    if isinstance(raw_input, str):  # input can be just one paragraph
        raw_input = [raw_input]

    input = "\n\n".join(raw_input).split("\n\n")
    result = ""
    for raw_line in input:
        # had an inspiration and wrote this; no idea how does it work exactly, it just does
        replaced_line = re.sub(r"(\s?\S?)((\x1b\[([0-9;]*)m)+)", push, raw_line)
        wrapped_line = f"\n".join(
            textwrap.wrap(
                replaced_line,
                width=width,
                initial_indent=(indent_first * " "),
                subsequent_indent=(indent_subseq * " "),
            )
        )
        final_line = re.sub(_PRIVATE_REPLACER, lambda _: sgrs.pop(0), wrapped_line)
        result += final_line + "\n"
    return result


codecs.register_error("replace_with_qmark", lambda e: ("?", e.start + 1))


# =============================================================================
# Filters

ESCAPE_SEQ_REGEX = re.compile(
    r"""
    (?P<escape_char>\x1b)
    (?P<data>
      (?P<nf_class_seq>
        (?P<nf_interm>[\x20-\x2f]+)
        (?P<nf_final>[\x30-\x7e])
      )|
      (?P<fp_class_seq>
        (?P<fp_classifier>[\x30-\x3f])
        (?P<fp_params>[\x20-\x7e]*)
        (?P<fp_terminator>)
      )|
      (?P<fe_class_seq>
        (?P<fe_classifier>[\x40-\x5f])
        (?P<fe_params>[\x30-\x3f]*)
        (?P<fe_termintaor>[\x40-\x5a])
      )|
      (?P<fs_class_seq>
        (?P<fs_classifier>[\x60-\x7e])
        (?P<fs_params>[\x20-\x7e]*)
        (?P<fs_termintaor>)
      )  
    )
""",
    flags=re.VERBOSE,
)
# https://ecma-international.org/wp-content/uploads/ECMA-35_6th_edition_december_1994.pdf

SGR_SEQ_REGEX = re.compile(r"(\x1b)(\[)([0-9;]*)(m)")
CSI_SEQ_REGEX = re.compile(r"(\x1b)(\[)(([0-9;:<=>?])*)([@A-Za-z])")

CONTROL_CHARS = [*range(0x00, 0x08 + 1), *range(0x0E, 0x1F + 1), 0x7F]
WHITESPACE_CHARS = [*range(0x09, 0x0D + 1), 0x20]
PRINTABLE_CHARS = [*range(0x21, 0x7E + 1)]
NON_ASCII_CHARS = [*range(0x80, 0xFF + 1)]

ALIGN_FUNCS_SGR = {
    Align.LEFT: ljust_sgr,
    Align.CENTER: center_sgr,
    Align.RIGHT: rjust_sgr,
}
ALIGN_FUNCS_RAW = {
    Align.LEFT: str.ljust,
    Align.CENTER: str.center,
    Align.RIGHT: str.rjust,
}

IT = t.TypeVar("IT", str, bytes)  # input-type
OT = t.TypeVar("OT", str, bytes)  # output-type
PT = Union[IT, t.Pattern[IT]]  # pattern type
RT = Union[OT, t.Callable[[t.Match[OT]], OT]]  # replacer type
MT = t.Dict[int, IT]  # map
AT = Union["OmniFilter", t.Type["OmniFilter"]]

_dump_printers_cache: t.Dict[t.Type["AbstractTracer"], "AbstractTracer"] = dict()


class IFilter(t.Generic[IT, OT], metaclass=ABCMeta):
    """
    Main idea is to provide a common interface for string filtering, that can make
    possible working with filters like with objects rather than with functions/lambdas.
    """

    def __call__(self, s: IT) -> OT:
        """Can be used instead of `apply()`"""
        return self.apply(s)

    @abstractmethod
    def apply(self, inp: IT, extra: t.Any = None) -> OT:
        """
        Apply the filter to input *str* or *bytes*.

        :param inp:   input string
        :param extra: additional options
        :return: transformed string; the type can match the input type,
                 as well as be different -- that depends on filter type.
        """
        raise NotImplementedError


class NoopFilter(IFilter[IT, OT]):
    """ """

    def apply(self, inp: IT, extra: t.Any = None) -> OT:
        return inp


class OmniDecoder(IFilter[IT, str]):
    """ """

    def apply(self, inp: IT, extra: t.Any = None) -> str:
        return inp.decode() if isinstance(inp, bytes) else inp


class OmniEncoder(IFilter[IT, bytes]):
    """ """

    def apply(self, inp: IT, extra: t.Any = None) -> bytes:
        return inp.encode() if isinstance(inp, str) else inp


class StringAligner(IFilter[str, str]):
    def __init__(self, align: Align):
        self._align = align

    def apply(self, inp: str, raw_mode: bool = False) -> str:
        pass

    def _get_align_fn(self, raw_mode: bool = False):
        if raw_mode:
            return ALIGN_FUNCS_RAW.get(self._align)
        return ALIGN_FUNCS_SGR.get(self._align)


# -----------------------------------------------------------------------------
# Filters[Tracers]


class AbstractTracer(IFilter[IT, str], metaclass=ABCMeta):
    def __init__(self, char_per_line: int):
        self._char_per_line = char_per_line
        self._state: _TracerState = _TracerState()

    def apply(self, inp: IT, extra: TracerExtra = None) -> str:
        if len(inp) == 0:
            return "\n"

        self._state.reset(inp)
        self._state.inp_size_len = len(str(self._state.inp_size))
        self._state.offset_len = len(self._format_offset(self._state.inp_size))

        while len(inp) > 0:
            inp, part = inp[self._char_per_line :], inp[: self._char_per_line]
            self._process(part)
            self._state.lineno += 1
            self._state.offset += self._char_per_line

        header = self._format_line_separator("_", f"{extra.label}" if extra else "")
        footer = self._format_line_separator(
            "-", label_right="(" + self._format_offset(self._state.inp_size) + ")"
        )

        result = header + "\n"
        result += "\n".join(self._render_rows())
        result += "\n" + footer + "\n"
        return result

    def _format_offset(self, override: int = None) -> str:
        offset = override or self._state.offset
        return str(offset).rjust(self._state.inp_size_len)

    def _format_line_separator(
        self, fill: str, label_left: str = "", label_right: str = ""
    ) -> str:
        return (
            label_left
            + fill * (self._get_output_line_len() - len(label_left) - len(label_right))
            + label_right
        )

    def _render_rows(self) -> t.Iterable[str]:
        for row in self._state.rows:
            row_str = ""
            for col_idx, col_val in enumerate(row):
                row_str += col_val.rjust(self._state.cols_max_len[col_idx])
            yield row_str

    def _get_vert_sep_char(self):
        return "|"

    def _get_output_line_len(self) -> int:
        # useless before processing
        if self._state.cols_max_len is None:
            return 0
        return sum(l for l in self._state.cols_max_len)

    @abstractmethod
    def _process(self, part: IT) -> str:
        raise NotImplementedError

    @classmethod
    def estimate_line_len(cls, char_per_line: int, inp_size: int) -> int:
        raise NotImplementedError


class BytesTracer(AbstractTracer[bytes]):
    """
    str/bytes as byte hex codes, grouped by 4

    .. code-block:: hexdump
       :caption: Example output

        0000  0A 20 32 31 36 20 20 20  E2 94 82 20 20 75 70 6C  |a
        0010  20 20 20 20 20 20 20 20  20 20 20 20 20 20 20 20  |a
    """

    GROUP_SIZE = 4

    def __init__(self, char_per_line: int = 32):
        super().__init__(self.GROUP_SIZE * ceil(char_per_line / self.GROUP_SIZE))

    def _process(self, part: IT):
        self._state.add_row(self._make_row(part))

    def _make_row(self, part: IT) -> t.List[str]:
        return [
            " ",
            self._format_offset(),
            " " + self._get_vert_sep_char() + "  ",
            *self._format_main(part),
        ]

    def _format_offset(self, override: int = None) -> str:
        offset = override or self._state.offset
        size_len = 2 * ceil(self._state.inp_size_len / 2)
        return f"{offset:0{size_len}X}"

    def _format_main(self, part: bytes) -> t.Iterable[str]:
        for c in chunk(part, self.GROUP_SIZE):
            yield (" ".join([f"{b:02X}" for b in (*c,)])).ljust(3 * self.GROUP_SIZE + 1)

    @classmethod
    def estimate_line_len(cls, char_per_line: int, inp_size: int) -> int:
        space_len = 4
        sep_len = 1
        offset_len = len(str(inp_size))
        main_len = (3 * char_per_line * cls.GROUP_SIZE) + (
            char_per_line // cls.GROUP_SIZE
        )
        return space_len + sep_len + offset_len + main_len


class AbstractStringTracer(AbstractTracer[str], metaclass=ABCMeta):
    def __init__(self, char_per_line: int):
        self._output_filters: t.List[IFilter] = []
        super().__init__(char_per_line)

    def _format_output_text(self, text: str) -> str:
        return apply_filters(text, *self._output_filters).ljust(self._char_per_line)


class StringTracer(AbstractStringTracer):
    """
    str as byte hex codes (UTF-8), grouped by characters

    .. code-block:: hexdump
       :caption: Example output

       0056  45 4D 20 43 50 55     20     4F 56 48 20 4E   45 3E 0A 20  |E|
       0072  20 20 20 20 20 20 E29482     20 20 20 20 20   20 20 20 20  |␣|
       0088  20 20 20 20 37 20     2B     30 20 20 20 20 CE94 20 32 68  |␣|
       0104  20 33 33 6D 20 20     20 EFAA8F 20 2D 35 20 C2B0 43 20 20  |␣|
    """

    def __init__(self, char_per_line: int = 16):
        super().__init__(char_per_line)
        self._output_filters = [NonPrintsStringVisualizer(keep_newlines=False)]

    def _process(self, part: IT):
        self._state.add_row(self._make_row(part))

    def _make_row(self, part: str) -> t.List[str]:
        return [
            " ",
            self._format_offset(),
            " " + self._get_vert_sep_char(),
            "0x",
            " ",
            *self._format_main(part),
            self._get_vert_sep_char(),
            self._format_output_text(part),
        ]

    def _format_main(self, part: str) -> t.Iterable[str]:
        for s in part:
            yield "".join(f"{b:02X}" for b in s.encode())
            yield " "
        yield from [""] * 2 * (self._char_per_line - len(part))

    @classmethod
    def estimate_line_len(cls, char_per_line: int, inp_size: int) -> int:
        space_len = 3
        sep_len = 6
        prefix_len = 2
        offset_len = len(str(inp_size))
        main_len = (8 + 1) * char_per_line
        return space_len + sep_len + prefix_len + offset_len + main_len


class StringUcpTracer(AbstractStringTracer):
    """
    str as Unicode codepoints

    .. todo::
        venv/lib/python3.8/site-packages/pygments/lexers/hexdump.py

    .. code-block:: bash
       :caption: Example output

        56 |U+ 45 4d 20 43 50 55   20   4f 56 48 20 4e  45 3e 0a 20 | EM␣CPU␣OVH␣NE>↵␣
        72 |U+ 20 20 20 20 20 20 2502   20 20 20 20 20  20 20 20 20 | ␣␣␣␣␣␣│␣␣␣␣␣␣␣␣␣
        88 |U+ 20 20 20 20 37 20   2b   30 20 20 20 20 394 20 32 68 | ␣␣␣␣7␣+0␣␣␣␣Δ␣2h
       104 |U+ 20 33 33 6d 20 20   20 fa8f 20 2d 35 20  b0 43 20 20 | ␣33m␣␣␣摒␣-5␣°C␣␣
    """

    def __init__(self, char_per_line: int = 16):
        super().__init__(char_per_line)
        self._output_filters = [NonPrintsStringVisualizer(keep_newlines=False)]

    def _process(self, part: IT):
        self._state.add_row(self._make_row(part))

    def _make_row(self, part: str) -> t.List[str]:
        return [
            " ",
            self._format_offset(),
            " " + self._get_vert_sep_char(),
            "U+",
            " ",
            *self._format_main(part),
            self._get_vert_sep_char(),
            self._format_output_text(part),
        ]

    def _format_main(self, part: str) -> t.Iterable[str]:
        for s in part:
            yield from [f"{ord(s):>02x}", " "]
        yield from [""] * 2 * (self._char_per_line - len(part))

    @classmethod
    def estimate_line_len(cls, char_per_line: int, inp_size: int) -> int:
        space_len = 3
        sep_len = 2
        prefix_len = 2
        offset_len = len(str(inp_size))
        main_len = (5 + 1) * char_per_line
        return space_len + sep_len + prefix_len + offset_len + main_len


@dataclass
class TracerExtra:
    label: str


@dataclass
class _TracerState:
    inp_size: int = field(init=False, default=None)
    lineno: int = field(init=False, default=None)
    offset: int = field(init=False, default=None)

    inp_size_len: int = field(init=False, default=None)
    offset_len: int = field(init=False, default=None)

    rows: t.List[t.List[str]] = field(init=False, default=None)
    cols_max_len: t.List[int] | None = field(init=False, default=None)

    def reset(self, inp: IT):
        self.inp_size = len(inp)
        self.lineno = 0
        self.offset = 0

        self.inp_size_len = 0
        self.offset_len = 0

        self.rows = []
        self.cols_max_len = None

    def add_row(self, row: t.List):
        if self.cols_max_len is None:
            self.cols_max_len = [0] * len(row)
        for col_idx, col_val in enumerate(row):
            self.cols_max_len[col_idx] = max(self.cols_max_len[col_idx], len(col_val))
        self.rows.append(row)


# -----------------------------------------------------------------------------
# Filters[Replacers]


class StringReplacer(IFilter[str, str]):
    """
    .
    """

    def __init__(self, pattern: PT[str], repl: RT[str]):
        if isinstance(pattern, str):
            self._pattern: t.Pattern[str] = re.compile(pattern)
        else:
            self._pattern: t.Pattern[str] = pattern
        self._repl = repl

    def apply(self, inp: str, extra: t.Any = None) -> str:
        return self._replace(inp)

    def _replace(self, inp: str) -> str:
        return self._pattern.sub(self._repl, inp)


class EscSeqStringReplacer(StringReplacer):
    """ """

    def __init__(self, repl: RT[str] = ""):
        super().__init__(ESCAPE_SEQ_REGEX, repl)


class SgrStringReplacer(StringReplacer):
    """
    Find all `SGR <SequenceSGR>` seqs (e.g., ``ESC [1;4m``) and replace with given string. More
    specific version of :class:`CsiReplacer`.

    :param repl:
        Replacement, can contain regexp groups (see :meth:`apply_filters()`).
    """

    def __init__(self, repl: RT[str] = ""):
        super().__init__(SGR_SEQ_REGEX, repl)


class CsiStringReplacer(StringReplacer):
    """
    Find all `CSI <SequenceCSI>` seqs (i.e., starting with ``ESC [``) and replace
    with given string. Less specific version of :class:`SgrReplacer`, as CSI
    consists of SGR and many other sequence subtypes.

    :param repl:
        Replacement, can contain regexp groups (see :meth:`apply_filters()`).
    """

    def __init__(self, repl: RT[str] = ""):
        super().__init__(CSI_SEQ_REGEX, repl)


# -----------------------------------------------------------------------------
# Filters[Mappers]


class OmniMapper(IFilter[IT, IT]):
    """
    Input type: *str*, *bytes*. Abstract mapper. Replaces every character found in
    map keys to corresponding map value. Map should be a dictionary of this type:
    ``dict[int, str|bytes|None]``; moreover, length of *str*/*bytes* must be strictly 1
    character (ASCII codepage). If there is a necessity to map Unicode characters,
    `StringMapper` should be used instead.

    >>> OmniMapper({0x20: '.'}).apply(b'abc def ghi')
    b'abc.def.ghi'

    For mass mapping it is better to subclass `OmniMapper` and override two methods --
    `_get_default_keys` and `_get_default_replacer`. In this case you don't have to
    manually compose a replacement map with every character you want to replace.

    :param override: a dictionary with mappings: keys must be *ints*, values must be
                     either a single-char *strs* or *bytes*, or None.
    :see: `NonPrintsOmniVisualizer`
    """

    def __init__(self, override: MT = None):
        self._make_maps(override)

    def _get_default_keys(self) -> t.List[int]:
        """
        Helper method for avoiding character map manual composing in the mapper subclass.

        :return: List of int codes that should be replaced by default (i.e., without
                 taking ``override`` argument into account, or when it is not present).
        """
        return []

    def _get_default_replacer(self) -> IT:
        """
        Helper method for avoiding character map manual composing in the mapper subclass.

        :return: Default replacement character for int codes that are not present in
                 ``override`` keys list, or when there is no overriding at all.
        """
        raise NotImplementedError

    def _make_maps(self, override: MT | None):
        self._maps = {
            str: str.maketrans(self._make_premap(str, override)),
            bytes: bytes.maketrans(*self._make_bytemaps(override)),
        }

    def _make_premap(self, inp_type: t.Type[IT], override: MT | None) -> t.Dict[int, IT]:
        default_map = dict()
        default_replacer = None
        for i in self._get_default_keys():
            if default_replacer is None:
                default_replacer = self._transcode(
                    self._get_default_replacer(), inp_type
                )
            default_map.setdefault(i, default_replacer)

        if override is None:
            return default_map
        if not isinstance(override, dict):
            raise ArgTypeError(type(override), "override", self.__init__)

        if not all(isinstance(k, int) and 0 <= k <= 255 for k in override.keys()):
            raise TypeError("Mapper keys should be ints such as: 0 <= key <= 255")
        if not all(isinstance(v, (str, bytes)) or v is None for v in override.values()):
            raise TypeError(
                "Each map value should be either a single char in 'str' or 'bytes' form, or None"
            )
        for i, v in override.items():
            default_map.update({i: self._transcode(v, inp_type)})
        return default_map

    def _make_bytemaps(self, override: MT | None) -> t.Tuple[bytes, bytes]:
        premap = self._make_premap(bytes, override)
        srcmap = b"".join(int.to_bytes(k, 1, "big") for k in premap.keys())
        for v in premap.values():
            if len(v) != 1:
                raise ValueError(
                    "All OmniMapper replacement values should be one byte long (i.e. be "
                    "an ASCII char). To utilize non-ASCII characters use StringMapper."
                )
        destmap = b"".join(premap.values())
        return srcmap, destmap

    def apply(self, inp: IT, extra: t.Any = None) -> IT:
        return inp.translate(self._maps[type(inp)])

    def _transcode(self, inp: IT, target: t.Type[RT]) -> RT:
        if isinstance(inp, target):
            return inp
        return inp.encode() if isinstance(inp, str) else inp.decode()


class StringMapper(OmniMapper[str]):
    """
    a
    """

    def _make_maps(self, override: MT | None):
        self._maps = {str: str.maketrans(self._make_premap(str, override))}

    def apply(self, inp: str, extra: t.Any = None) -> str:
        if isinstance(inp, bytes):
            raise TypeError("String mappers allow 'str' as input only")
        return super().apply(inp, extra)


class NonPrintsOmniVisualizer(OmniMapper):
    """
    Input type: *str*, *bytes*. Replace every whitespace character with ``.``.
    """

    def _get_default_keys(self) -> t.List[int]:
        return WHITESPACE_CHARS + CONTROL_CHARS

    def _get_default_replacer(self) -> IT:
        return b"."


class NonPrintsStringVisualizer(StringMapper):
    """
    Input type: *str*. Replace every whitespace character with "·", except
    newlines. Newlines are kept and get prepneded with same char by default,
    but this behaviour can be disabled with ``keep_newlines`` = *False*.

    >>> NonPrintsStringVisualizer().apply('A  B  C')
    'A␣␣B␣␣C'
    >>> apply_filters('1. D'+os.linesep+'2. L ', NonPrintsStringVisualizer(keep_newlines=False))
    '1.␣D↵2.␣L␣'

    :param keep_newlines: When *True*, transform newline characters into "↵\\\\n", or
                          into just "↵" otherwise.
    """

    def __init__(self, keep_newlines: bool = True):
        override = {
            0x09: "⇥",
            0x0A: "↵" + ("\n" if keep_newlines else ""),
            0x0B: "⤓",
            0x0C: "↡",
            0x0D: "⇤",
            0x20: "␣",
        }
        super().__init__(override)

    def _get_default_keys(self) -> t.List[int]:
        return WHITESPACE_CHARS + CONTROL_CHARS

    def _get_default_replacer(self) -> str:
        return "·"


class OmniSanitizer(OmniMapper):
    """
    Input type: *str*, *bytes*. Replace every control character and every non-ASCII
    character (0x80-0xFF) with ".", or with specified char. Note that the replacement
    should be a single ASCII character, because ``Omni-`` filters are designed to work
    with *str* inputs and *bytes* inputs on equal terms.

    :param repl: Value to replace control/non-ascii characters with. Should be strictly 1
                 character long.
    """

    def __init__(self, repl: IT = b"."):
        self._override_replacer = repl
        super().__init__()

    def _get_default_keys(self) -> t.List[int]:
        return CONTROL_CHARS + NON_ASCII_CHARS

    def _get_default_replacer(self) -> IT:
        return self._override_replacer


# -----------------------------------------------------------------------------


def apply_filters(string: IT, *args: AT) -> OT:
    """
    Method for applying dynamic filter list to a target string/bytes.
    Example (will replace all ``ESC`` control characters to ``E`` and
    thus make SGR params visible):

    >>> from pytermor import SeqIndex
    >>> apply_filters(f'{SeqIndex.RED}test{SeqIndex.COLOR_OFF}', SgrStringReplacer(r'E\2\3\4'))
    'E[31mtestE[39m'

    Note that type of ``s`` argument must be same as ``StringFilter`` parameterized
    type, i.e. :class:`ReplaceNonAsciiBytes` is ``StringFilter`` type, so
    you can apply it only to bytes-type strings.

    :param string: String to filter.
    :param args:   `OmniFilter` instance(s) or ``OmniFilter`` type(s).
    :return:       Filtered ``s``.
    """

    def instantiate(f):
        return f() if isinstance(f, type) else f

    return reduce(lambda s, f: instantiate(f)(s), args, string)


def dump(data: t.Any, label: str = None, max_len_shift: int = None) -> str | None:
    """
    .. todo ::
        - format selection
        - special handling of one-line input
        - squash repeating lines
    """
    printer_t = StringUcpTracer
    printer = _dump_printers_cache.get(printer_t, None)

    if not printer and max_len_shift is not None:
        max_len = get_terminal_width() + max_len_shift
        for chars_per_line in [8, 12, 16, 20, 24, 32, 40, 48, 64]:
            est_len = printer_t.estimate_line_len(chars_per_line, len(data))
            if est_len < max_len:
                printer = printer_t(chars_per_line)
                continue
            break

    if not printer:
        printer = printer_t()
    _dump_printers_cache[printer_t] = printer

    return printer.apply(data, TracerExtra(label))
