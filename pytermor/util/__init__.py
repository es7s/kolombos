# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
.. testsetup:: *

    from pytermor.util import format_thousand_sep

"""
from __future__ import annotations

from .auto_float import format_auto_float
from .prefixed_unit import format_si_metric, format_si_binary, PrefixedUnitFormatter, PREFIXES_SI, PREFIX_ZERO_SI
from .time_delta import format_time_delta, TimeUnit, TimeDeltaFormatter

from .string_filter import apply_filters, StringFilter, ReplaceSGR, ReplaceCSI, ReplaceNonAsciiBytes, VisualuzeWhitespace
from .stdlib_ext import ljust_sgr, rjust_sgr, center_sgr


def format_thousand_sep(value: int|float, separator=' '):
    """
    Returns input ``value`` with integer part splitted into groups of three digits,
    joined then with ``separator`` string.

    >>> format_thousand_sep(260341)
    '260 341'
    >>> format_thousand_sep(-9123123123.55, ',')
    '-9,123,123,123.55'

    """
    return f'{value:_}'.replace('_', separator)

