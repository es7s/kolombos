# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
.. testsetup:: *

    from pytermor.util.prefixed_unit import format_si_metric, format_si_binary

"""
from __future__ import annotations

from math import trunc
from typing import List

from .auto_float import format_auto_float


def format_si_metric(value: float, unit: str = 'm') -> str:
    """
    Format ``value`` as meters with SI-prefixes, max
    result length is *6* chars. Base is *1000*. Unit can be
    customized.

    >>> format_si_metric(123.456)
    '123 m'
    >>> format_si_metric(0.331, 'g')
    '331 mg'
    >>> format_si_metric(45200, 'V')
    '45.2 kV'
    >>> format_si_metric(1.26e-9, 'm²')
    '1.26 nm²'

    :param value: Input value (unitless).
    :param unit:  Value unit, printed right after the prefix.
    :return:      Formatted string with SI-prefix if necessary.

    .. versionadded:: 2.0
    """
    return _formatter_si_metric.format(value, unit)


def format_si_binary(value: float, unit: str = 'b') -> str:
    """
    Format ``value`` as binary size (bytes, kbytes, Mbytes), max
    result length is *8* chars. Base is *1024*. Unit can be
    customized.

    >>> format_si_binary(631)
    '631 b'
    >>> format_si_binary(1080)
    '1.055 kb'
    >>> format_si_binary(45200)
    '44.14 kb'
    >>> format_si_binary(1.258 * pow(10, 6), 'bps')
    '1.200 Mbps'

    :param value: Input value in bytes.
    :param unit:  Value unit, printed right after the prefix.
    :return:      Formatted string with SI-prefix if necessary.

    .. versionadded:: 2.0
    """
    return _formatter_si_binary.format(value, unit)


class PrefixedUnitFormatter:
    """
    Formats ``value`` using settings passed to constructor. The main idea of this class
    is to fit into specified string length as much significant digits as it's
    theoretically possible by using multipliers and unit prefixes to
    indicate them.

    You can create your own formatters if you need fine tuning of the
    output and customization. If that's not the case, there are facade
    methods :meth:`format_si_metric()` and :meth:`format_si_binary()`,
    which will invoke predefined formatters and doesn't require setting up.

    .. todo :: params

    :param prefix_zero_idx:
            Index of prefix which will be used as default, i.e. without multiplying coefficients.

    .. versionadded:: 1.7
    """
    def __init__(self, max_value_len: int, truncate_frac: bool = False, unit: str = None, unit_separator: str = None,
                 mcoef: float = 1000.0, prefixes: List[str | None] = None, prefix_zero_idx: int = None):
        self._max_value_len: int = max_value_len
        self._truncate_frac: bool = truncate_frac
        self._unit: str = unit or ''
        self._unit_separator: str = unit_separator or ''
        self._mcoef: float = mcoef
        self._prefixes: List[str | None] = prefixes or []
        self._prefix_zero_idx: int = prefix_zero_idx or 0

    @property
    def max_len(self) -> int:
        """
        :return: Maximum length of the result. Note that constructor argument
                 is `max_value_len`, which is different parameter.
        """
        result = self._max_value_len
        result += len(self._unit_separator)
        result += len(self._unit)
        result += max([len(p) for p in self._prefixes if p])
        return result

    def format(self, value: float, unit: str = None) -> str:
        """
        :param value:  Input value
        :param unit:   Unit override
        :return:       Formatted value
        """
        unit_idx = self._prefix_zero_idx

        while 0 <= unit_idx < len(self._prefixes):
            if 0.0 < abs(value) <= 1 / self._mcoef:
                value *= self._mcoef
                unit_idx -= 1
                if abs(value) <= 1:
                    continue
            elif abs(value) >= self._mcoef:
                value /= self._mcoef
                unit_idx += 1
                continue

            unit_full = (self._prefixes[unit_idx] or '') + \
                        (unit or self._unit)

            if self._truncate_frac and unit_idx == self._prefix_zero_idx:
                num_str = f'{trunc(value)!s:.{self._max_value_len}s}'
            else:
                num_str = format_auto_float(value,
                                            self._max_value_len,
                                            allow_exponent_notation=False)

            return f'{num_str.strip()}{self._unit_separator}{unit_full.strip()}'

        # no more prefixes left
        num_str = format_auto_float(value,
                                    self._max_value_len,
                                    allow_exponent_notation=False)
        unit_full = ('?' * max([len(p) for p in self._prefixes if p])) + self._unit
        return f'{num_str.strip()}{self._unit_separator}{unit_full.strip()}'


# ---------------------------------------------------------------------------
# Preset formatters
# ---------------------------------------------------------------------------

PREFIXES_SI = ['y', 'z', 'a', 'f', 'p', 'n', 'μ', 'm', None, 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
"""
Prefix presets used by default module formatters. Can be
useful if you are building your own formatter.
"""
PREFIX_ZERO_SI = 8
"""
Index of prefix which will be used as default, i.e. without 
multiplying coefficients.
"""

_formatter_si_metric = PrefixedUnitFormatter(
    max_value_len=4,
    truncate_frac=False,
    unit='',
    unit_separator=' ',
    mcoef=1000.0,
    prefixes=PREFIXES_SI,
    prefix_zero_idx=PREFIX_ZERO_SI,
)
"""
Suitable for formatting any SI unit with values
from approximately ``10^-27`` to ``10^27``.

``max_value_len`` must be at least **4**, because it's a
minimum requirement for formatting values from ``999`` to ``-999``.
Next number to 999 is ``1000``, which will be formatted as "1k".

Total maximum length is ``max_value_len + 3``, which is **7** 
(+3 is from separator, unit and prefix, assuming all of them
have 1-char width). Without unit (default) it's **6**.
"""

_formatter_si_binary = PrefixedUnitFormatter(
    max_value_len=5,
    truncate_frac=True,
    unit='b',
    unit_separator=' ',
    mcoef=1024.0,
    prefixes=PREFIXES_SI,
    prefix_zero_idx=PREFIX_ZERO_SI,
)
"""
Similar to `_formatter_si_metric`, but this formatter differs in 
one aspect.  Given a variable with default value = ``995``,
formatting it's value results in "995 b". After increasing it 
by ``20`` we'll have ``1015``, but it's still not enough to become 
a kilobyte -- so returned value will be "1015 b". Only after one 
more increase (at ``1024`` and more) the value will be in a form
of "1.00 kb".  

So, in this case ``max_value_len`` must be at least **5** (not 4),
because it's a minimum requirement for formatting values from ``1023`` 
to ``-1023``.

Total maximum length is ``max_value_len + 3`` = **8** (+3 is from separator,
unit and prefix, assuming all of them have 1-char width).
"""
