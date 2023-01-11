# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
.. testsetup:: *

    from pytermor.util.auto_float import format_auto_float

"""
from math import trunc, log10, floor


_OVERFLOW_CHAR = '!'


def format_auto_float(value: float, req_len: int, allow_exponent_notation: bool = True) -> str:
    """
    Dynamically adjust decimal digit amount and format
    to fill up the output string with as many significant
    digits as possible, and keep the output length
    strictly equal to `req_len`  at the same time.

    >>> format_auto_float(0.016789, 5)
    '0.017'
    >>> format_auto_float(0.167891, 5)
    '0.168'
    >>> format_auto_float(1.567891, 5)
    '1.568'
    >>> format_auto_float(12.56789, 5)
    '12.57'
    >>> format_auto_float(123.5678, 5)
    '123.6'
    >>> format_auto_float(1234.567, 5)
    ' 1235'
    >>> format_auto_float(12345.67, 5)
    '12346'

    For cases when it's impossible to fit a number in the required length
    and rounding doesn't help (e.g. 12 500 000 and 5 chars) algorithm
    switches to scientific notation and the result looks like '1.2e7'.

    When exponent form is disabled, there are two options for value that cannot
    fit into required length:

    1) if absolute value is less than 1, zeros will be displayed ('0.0000');
    2) in case of big numbers (like 10\ :sup:`9`) ValueError will be raised instead.

    :param value:   Value to format
    :param req_len: Required output string length
    :param allow_exponent_notation: Enable/disable exponent form.

    :return: Formatted string of required length
    :except ValueError:

    .. versionadded:: 1.7
    """
    if req_len < -1:
        raise ValueError(f'Required length should be >= 0 (got {req_len})')

    sign = ''
    if value < 0:
        sign = '-'
        req_len -= 1

    if req_len == 0:
        return _OVERFLOW_CHAR * (len(sign))

    abs_value = abs(value)
    if abs_value < 1 and req_len == 1:
        # '0' is better than '-'
        return f'{sign}0'

    if value == 0.0:
        return f'{sign}{0:{req_len}.0f}'

    exponent = floor(log10(abs_value))
    exp_threshold_left = -2
    exp_threshold_right = req_len - 1

    # exponential mode threshold depends
    # on mareqx length on the right, and is
    # fixed to -2 on the left:

    #   req |    3     4     5     6 |
    #  thld | -2,2  -2,3  -2,4  -2,5 |

    # it determines exponent values to
    # enable exponent notation for:

    #  value exp req thld cnd result |
    # ------ --- --- ---- --- ------ |
    # 0.0001  -4   4 -2,3   t   1e-4 |
    #  0.001  -3   4 -2,3   f   1e-3 | - less than threshold
    #   0.01  -2   4 -2,3   f   0.01 | ---- N -
    #    0.1  -1   4 -2,3   f   0.10 |      O M
    #      1   0   4 -2,3   f   1.00 |      R O
    #     10   1   4 -2,3   f   10.0 |      M D
    #    100   2   4 -2,3   f  100.0 |      A E
    #   1000   3   4 -2,3   f   1000 | ---- L -
    #  10000   4   4 -2,3   t    1e4 | - greater than threshold

    if not allow_exponent_notation:
        # if exponent mode is disabled, we will try as best
        # as we can to display at least something significant;
        # this can work for some of the values around the zero
        # (and result in like '0.00001'), but not for very big ones.
        exp_threshold_left = None

    required_exponent = (
        (exp_threshold_left is not None and exponent < exp_threshold_left) or
        exponent > exp_threshold_right
    )

    if required_exponent:
        if not allow_exponent_notation:  # oh well...
            raise ValueError(f'Failed to fit {value:.2f} into {req_len} chars without scientific notation')

        exponent_len = len(str(exponent)) + 1  # 'e'
        if req_len < exponent_len:
            # there is no place even for exponent
            return _OVERFLOW_CHAR * (len(sign) + req_len)

        significand = abs_value/pow(10, exponent)
        max_significand_len = req_len - exponent_len
        try:
            # max_significand_len can be 0, in that case significand_str will be empty; that
            # means we cannot fit it the significand, but still can display approximate number power
            # using the 'eN'/'-eN' notation
            significand_str = format_auto_float(significand, max_significand_len, allow_exponent_notation=False)

        except ValueError:
            return f'{sign}e{exponent}'.rjust(req_len)

        return f'{sign}{significand_str}e{exponent}'

    integer_len = max(1, exponent + 1)
    if integer_len == req_len:
        # special case when rounding
        # can change the result length
        integer_str = f'{abs_value:{req_len}.0f}'

        if len(integer_str) > integer_len:
            # e.g. req_len = 1, abs_value = 9.9
            #      => should be displayed as 9, not 10
            integer_str = f'{trunc(abs_value):{req_len}d}'

        return f'{sign}{integer_str}'

    decimals_with_point_len = req_len - integer_len
    decimals_len = decimals_with_point_len - 1

    # dot without decimals makes no sense, but
    # python's standard library handles
    # this by itself: f'{12.3:.0f}' => '12'
    dot_str = f'.{decimals_len!s}'

    return f'{sign}{abs_value:{req_len}{dot_str}f}'
