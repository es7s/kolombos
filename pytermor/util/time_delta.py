# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
Module for time difference formatting (e.g. "4 days 15 hours", "8h 59m").

Supports several output lengths and can be customized even more.

.. testsetup:: *

    from pytermor.util.time_delta import format_time_delta

"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, trunc, isclose
from typing import List, Dict

from .stdlib_ext import rjust_sgr


def format_time_delta(seconds: float, max_len: int = None) -> str:
    """
    Format time delta using suitable format (which depends on
    ``max_len`` argument). Key feature of this formatter is
    ability to combine two units and display them simultaneously,
    e.g. return "3h 48min" instead of "228 mins" or "3 hours",

    There are predefined formatters with output length of 3, 4,
    6 and 10 characters. Therefore, you can pass in any value
    from 3 inclusive and it's guarenteed that result's length
    will be less or equal to required length. If `max_len` is
    omitted, longest registred formatter will be used.

    >>> format_time_delta(10, 3)
    '10s'
    >>> format_time_delta(10, 6)
    '10 sec'
    >>> format_time_delta(15350, 4)
    '4 h'
    >>> format_time_delta(15350)
    '4h 15min'

    :param seconds: Value to format
    :param max_len: Maximum output string length (total)
    :return:        Formatted string
    """
    if max_len is None:
        formatter = registry.get_longest()
    else:
        formatter = registry.find_matching(max_len)

    if formatter is None:
        raise ValueError(f'No settings defined for max length = {max_len} (or less)')

    return formatter.format(seconds)


class TimeDeltaFormatter:
    """
    Formatter for time intervals. Key feature of this formatter is
    ability to combine two units and display them simultaneously,
    e.g. return "3h 48min" instead of "228 mins" or "3 hours", etc.

    You can create your own formatters if you need fine tuning of the
    output and customization. If that's not the case, there is a
    facade method :meth:`format_time_delta()` which will select appropriate
    formatter automatically.

    Example output::

        "10 secs", "5 mins", "4h 15min", "5d 22h"

    """
    def __init__(self, units: List[TimeUnit], allow_negative: bool, unit_separator: str = None,
                 plural_suffix: str = None,  overflow_msg: str = 'OVERFLOW'):
        self._units = units
        self._allow_negative = allow_negative
        self._unit_separator = unit_separator
        self._plural_suffix = plural_suffix
        self._overflow_msg = overflow_msg

        self._max_len = self._compute_max_len()

    @property
    def max_len(self) -> int:
        """
        This property cannot be set manually, it is
        computed on initialization automatically.

        :return: Maximum possible output string length.
        """
        return self._max_len

    def format(self, seconds: float, always_max_len: bool = False) -> str:
        """
        Pretty-print difference between two moments in time.

        :param seconds: Input value.
        :param always_max_len:
                         If result string is less than `max_len` it will be returned
                         as is, unless this flag is set to *True*. In that case output
                         string will be padded with spaces on the left side so that
                         resulting length would be always equal to maximum length.
        :return:  Formatted string.
        """
        result = self.format_raw(seconds)
        if result is None:
            result = self._overflow_msg[:self.max_len]

        if always_max_len:
            result = rjust_sgr(result, self._max_len)

        return result

    def format_raw(self, seconds: float) -> str|None:
        """
        Pretty-print difference between two moments in time, do not replace
        the output with "OVERFLOW" warning message.

        :param seconds: Input value.
        :return:        Formatted string or *None* on overflow (if input
                        value is too big for the current formatter to handle).
        """
        num = abs(seconds)
        unit_idx = 0
        prev_frac = ''

        negative = self._allow_negative and seconds < 0
        sign = '-' if negative else ''
        result = None

        while result is None and unit_idx < len(self._units):
            unit = self._units[unit_idx]
            if unit.overflow_afer and num > unit.overflow_afer:
                if not self._max_len:  # max len is being computed now
                    raise RecursionError()
                return None

            unit_name = unit.name
            unit_name_suffixed = unit_name
            if self._plural_suffix and trunc(num) != 1:
                unit_name_suffixed += self._plural_suffix

            short_unit_name = unit_name[0]
            if unit.custom_short:
                short_unit_name = unit.custom_short

            next_unit_ratio = unit.in_next
            unit_separator = self._unit_separator or ''

            if abs(num) < 1:
                if negative:
                    result = f'~0{unit_separator}{unit_name_suffixed:s}'
                elif isclose(num, 0, abs_tol=1e-03):
                    result = f'0{unit_separator}{unit_name_suffixed:s}'
                else:
                    result = f'<1{unit_separator}{unit_name:s}'

            elif unit.collapsible_after is not None and num < unit.collapsible_after:
                result = f'{sign}{floor(num):d}{short_unit_name:s}{unit_separator}{prev_frac:<s}'

            elif not next_unit_ratio or num < next_unit_ratio:
                result = f'{sign}{floor(num):d}{unit_separator}{unit_name_suffixed:s}'

            else:
                next_num = floor(num / next_unit_ratio)
                prev_frac = '{:d}{:s}'.format(floor(num - (next_num * next_unit_ratio)), short_unit_name)
                num = next_num
                unit_idx += 1
                continue

        return result or ''

    def _compute_max_len(self) -> int:
        max_len = 0
        coef = 1.00

        for unit in self._units:
            test_val = unit.in_next
            if not test_val:
                test_val = unit.overflow_afer
            if not test_val:
                continue
            test_val_seconds = coef * (test_val - 1) * (-1 if self._allow_negative else 1)

            try:
                max_len_unit = self.format_raw(test_val_seconds)
            except RecursionError:
                continue

            max_len = max(max_len, len(max_len_unit))
            coef *= unit.in_next or unit.overflow_afer

        return max_len


@dataclass(frozen=True)
class TimeUnit:
    name: str
    in_next: int = None             # how many current units equal to the (one) next unit
    custom_short: str = None
    collapsible_after: int = None   # min threshold for double-delta to become regular
    overflow_afer: int = None       # max threshold


class _TimeDeltaFormatterRegistry:
    """
    Simple registry for storing formatters and selecting
    the suitable one by max output length.
    """
    def __init__(self):
        self._formatters: Dict[int, TimeDeltaFormatter] = dict()

    def register(self, *formatters: TimeDeltaFormatter):
        for formatter in formatters:
            self._formatters[formatter.max_len] = formatter

    def find_matching(self, max_len: int) -> TimeDeltaFormatter | None:
        exact_match = self.get_by_max_len(max_len)
        if exact_match is not None:
            return exact_match

        suitable_max_len_list = sorted(
            [key for key in self._formatters.keys() if key <= max_len],
            key=lambda k: k,
            reverse=True,
        )
        if len(suitable_max_len_list) == 0:
            return None
        return self.get_by_max_len(suitable_max_len_list[0])

    def get_by_max_len(self, max_len: int) -> TimeDeltaFormatter | None:
        return self._formatters.get(max_len, None)

    def get_shortest(self) -> _TimeDeltaFormatterRegistry | None:
        return self._formatters.get(min(self._formatters.keys() or [None]))

    def get_longest(self) -> _TimeDeltaFormatterRegistry | None:
        return self._formatters.get(max(self._formatters.keys() or [None]))


# ---------------------------------------------------------------------------
# Preset formatters
# ---------------------------------------------------------------------------

registry = _TimeDeltaFormatterRegistry()
registry.register(
    TimeDeltaFormatter([
        TimeUnit('s', 60),
        TimeUnit('m', 60),
        TimeUnit('h', 24),
        TimeUnit('d', overflow_afer=99),
    ], allow_negative=False,
        unit_separator=None,
        plural_suffix=None,
        overflow_msg='ERR',
    ),

    TimeDeltaFormatter([
        TimeUnit('s', 60),
        TimeUnit('m', 60),
        TimeUnit('h', 24),
        TimeUnit('d', 30),
        TimeUnit('M', 12),
        TimeUnit('y', overflow_afer=99),
    ], allow_negative=False,
        unit_separator=' ',
        plural_suffix=None,
        overflow_msg='ERRO',
    ),

    TimeDeltaFormatter([
        TimeUnit('sec', 60),
        TimeUnit('min', 60),
        TimeUnit('hr', 24, collapsible_after=10),
        TimeUnit('day', 30, collapsible_after=10),
        TimeUnit('mon', 12),
        TimeUnit('yr', overflow_afer=99),
    ], allow_negative=False,
        unit_separator=' ',
        plural_suffix=None,
    ),

    TimeDeltaFormatter([
        TimeUnit('sec', 60),
        TimeUnit('min', 60, custom_short='min'),
        TimeUnit('hour', 24, collapsible_after=24),
        TimeUnit('day', 30, collapsible_after=10),
        TimeUnit('month', 12),
        TimeUnit('year', overflow_afer=999),
    ], allow_negative=True,
        unit_separator=' ',
        plural_suffix='s',
    ),
)
