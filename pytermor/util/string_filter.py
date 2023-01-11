# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
String filtering module.

Main idea is to provide a common interface for string filtering, that can make
possible working with filters like with objects rather than with functions/lambdas.

.. testsetup:: *

    from pytermor.ansi import Spans
    from pytermor.util.string_filter import apply_filters, ReplaceSGR, VisualuzeWhitespace

"""
from __future__ import annotations

import re
from functools import reduce
from re import Match, Pattern
from typing import Generic, AnyStr, Type, Callable

from ..ansi import Spans


SGR_REGEXP = re.compile(r'(\x1b)(\[)(([0-9;])*)(m)')


def apply_filters(s: AnyStr, *args: StringFilter[AnyStr]|Type[StringFilter[AnyStr]]) -> AnyStr:  # @FIXME StringFilter[AnyStr] -> StringFilter ?
    """
    Method for applying dynamic filter list to a target string/bytes.
    Example (will replace all :kbd:`ESC` control characters to :kbd:`E` and
    thus make SGR params visible):

    >>> apply_filters(Spans.RED('test'), ReplaceSGR(r'E\\2\\3\\5'))
    'E[31mtestE[39m'

    Note that type of ``s`` argument must be same as ``StringFilter`` parameterized
    type, i.e. :class:`ReplaceNonAsciiBytes` is ``StringFilter[bytes]`` type, so
    you can apply it only to bytes-type strings.

    :param AnyStr s: String to filter.
    :param args:     `StringFilter` instance(s) or ``StringFilter`` class(es).
    :return:         Filtered ``s``.
    """
    filters = map(lambda t: t() if isinstance(t, type) else t, args)
    return reduce(lambda s_, f: f.apply(s_), filters, s)


class StringFilter(Generic[AnyStr]):
    """
    Common string modifier interface.
    """
    def __init__(
        self,
        pattern: AnyStr|Pattern[AnyStr],
        repl: AnyStr|Callable[[AnyStr|Match], AnyStr]
    ):
        if isinstance(pattern, (str, bytes)):
            self._regex = re.compile(pattern)
        else:
            self._regex = pattern
        self._repl = repl

    def __call__(self, s: AnyStr) -> AnyStr:
        """ Can be used instead of `apply()` """
        return self.apply(s)

    def apply(self, s: AnyStr) -> AnyStr:
        """ Apply filter to ``s`` string (or bytes). """
        return self._regex.sub(self._repl, s)


class VisualuzeWhitespace(StringFilter[str]):
    """
    Replace every invisible character with ``repl`` (default is :kbd:`·`),
    except newlines. Newlines are kept and get prepneded with same string.

    >>> VisualuzeWhitespace().apply('A  B  C')
    'A··B··C'
    >>> apply_filters('1. D\\n2. L ', VisualuzeWhitespace)
    '1.·D·\\n2.·L·'
    """
    def __init__(self, repl: AnyStr = '·'):
        super().__init__(r'(\n)|\s', repl + '\\1')


class ReplaceSGR(StringFilter[str]):
    """
    Find all SGR seqs (e.g. :kbd:`ESC[1;4m`) and replace with given string. More
    specific version of :class:`ReplaceCSI`.

    :param repl:
        Replacement, can contain regexp groups (see :meth:`apply_filters()`).
    """
    def __init__(self, repl: AnyStr = ''):
        super().__init__(SGR_REGEXP, repl)


class ReplaceCSI(StringFilter[str]):
    """
    Find all CSI seqs (i.e. :kbd:`ESC[*`) and replace with given string. Less
    specific version of :class:`ReplaceSGR`, as CSI consists of SGR and many other
    sequence subtypes.

    :param repl:
        Replacement, can contain regexp groups (see :meth:`apply_filters()`).
    """
    def __init__(self, repl: AnyStr = ''):
        super().__init__(r'(\x1b)(\[)(([0-9;:<=>?])*)([@A-Za-z])', repl)


class ReplaceNonAsciiBytes(StringFilter[bytes]):
    """
    Keep 7-bit ASCII bytes [:kbd:`0x00` - :kbd:`0x7f`], replace other to :kbd:`?`.

    :param repl: Replacement byte-string.
    """
    def __init__(self, repl: AnyStr = b'?'):
        super().__init__(b'[\x80-\xff]', repl)
