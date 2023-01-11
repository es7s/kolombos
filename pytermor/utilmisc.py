# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022-2023. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
A
"""

from __future__ import annotations

import functools
import itertools
import math
import os
import sys
import threading
import time
import typing as t
import unicodedata
from collections import deque
from io import StringIO
from itertools import chain
from sys import getsizeof, stderr

from .ansi import (
    make_query_cursor_position,
    decompose_request_cursor_position,
    make_erase_in_line,
    make_set_cursor_x_abs,
)
from .common import UserAbort, UserCancel

T = t.TypeVar("T")


def get_qname(obj: t.Any) -> str:
    """
    Convenient method for getting a class name for class instances
    as well as for the classes themselves. Suitable for debug output in
    ``__repr__`` methods, for example.

    >>> get_qname("aaa")
    'str'
    >>> get_qname(make_query_cursor_position())
    'SequenceCSI'
    >>> get_qname(threading.Thread)
    'Thread'

    """
    if isinstance(obj, type):
        return obj.__qualname__
    if isinstance(obj, object):
        return obj.__class__.__qualname__
    return str(obj)


def chunk(items: t.Iterable[T], size: int) -> t.Iterator[t.Tuple[T, ...]]:
    """
    Split item list into chunks of size ``size`` and return these
    chunks as *tuples*.

    >>> for c in chunk(range(5), 2):
    ...     print(c)
    (0, 1)
    (2, 3)
    (4,)

    :param items:  Input elements.
    :param size:   Chunk size.
    """
    arr_range = iter(items)
    return iter(lambda: tuple(itertools.islice(arr_range, size)), ())


def flatten1(items: t.Iterable[t.Iterable[T]]) -> t.List[T]:
    """
    Take a list of nested lists and unpack all nested elements one level up.

    >>> flatten1([[1, 2, 3], [4, 5, 6], [[10, 11, 12]]])
    [1, 2, 3, 4, 5, 6, [10, 11, 12]]

    :param items:  Input lists.
    """
    return list(itertools.chain.from_iterable(items))


def flatten(items: t.Iterable[t.Iterable[T]]) -> t.List[T]:
    """
    .. todo ::
        recursrive
    """


def percentile(
    N: t.Sequence[float], percent: float, key: t.Callable[[float], float] = lambda x: x
) -> float:
    """
    Find the percentile of a list of values.

    :origin:         https://code.activestate.com/recipes/511478/
    :param N:        List of values. MUST BE already sorted.
    :param percent:  Float value from 0.0 to 1.0.
    :param key:      Optional key function to compute value from each element of N.
    """
    if not N:
        raise ValueError("N should be a non-empty sequence of floats")
    k = (len(N) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c - k)
    d1 = key(N[int(c)]) * (k - f)
    return d0 + d1


def median(N: t.Sequence[float], key: t.Callable[[float], float] = lambda x: x) -> float:
    """
    Find the median of a list of values.
    Wrapper around `percentile()` with fixed ``percent`` argument (=0.5).

    :param N:    List of values. MUST BE already sorted.
    :param key:  Optional key function to compute value from each element of N.
    """
    return percentile(N, percent=0.5, key=key)


# -----------------------------------------------------------------------------


def get_terminal_width(fallback: int = 80, pad: int = 2) -> int:
    """
    Return current terminal width with an optional "safety buffer", which
    ensures that no unwanted line wrapping will happen.

    :param fallback: Default value when shutil is unavailable and environment
                     variable COLUMNS is unset.
    :param pad:      Additional safety space to prevent unwanted line wrapping.
    """
    try:
        import shutil as _shutil

        return _shutil.get_terminal_size().columns - pad
    except ImportError:
        pass

    try:
        return int(os.environ.get("COLUMNS", fallback))
    except ValueError:
        pass

    return fallback


def get_preferable_wrap_width(force_width: int = None) -> int:
    """
    Return preferable terminal width for comfort reading of wrapped text (max=120).

    :param force_width:
               Ignore current terminal width and use this value as a result.
    """
    if isinstance(force_width, int) and force_width > 1:
        return force_width
    return min(120, get_terminal_width())


def wait_key() -> t.AnyStr | None:
    """
    Wait for a key press on the console and return it.

    :raises EOFError:
    """
    if os.name == "nt":
        import msvcrt

        return msvcrt.getch()
    import termios

    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    result = None
    try:
        result = sys.stdin.read(1)
    except IOError:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
    return result


def confirm(
    attempts: int = 1,
    default: bool = False,
    keymap: t.Mapping[str, bool] = None,
    prompt: str = None,
    quiet: bool = False,
    required: bool = False,
) -> bool:
    """
    Ensure the next action is manually confirmed by user. Print the terminal
    prompt with ``prompt`` text and wait for a keypress. Return *True*
    if user pressed :kbd:`Y` and *False* in all the other cases (by default).

    Valid keys are :kbd:`Y` and :kbd:`N` (case insensitive), while all the other keys
    and combinations are considered invalid, and will trigger the return of the
    ``default`` value, which is *False* if not set otherwise. In other words,
    by default the user is expected to press either :kbd:`Y` or :kbd:`N`, and if
    that's not the case, the confirmation request will be automatically failed.

    :kbd:`Ctrl+C` instantly aborts the confirmation process regardless of attempts
    count and raises `UserAbort`.

    Example keymap (default one)::

        keymap = {"y": True, "n": False}

    :param attempts:    Set how many times the user is allowed to perform the
                        input before auto-cancellation (or auto-confirmation) will
                        occur. 1 means there will be only one attempt, the first one.
                        When set to -1, allows to repeat the input infinitely.
    :param default:     Default value that will be returned when user presses invalid
                        key (e.g. :kbd:`Backspace`, :kbd:`Ctrl+Q` etc.) and his
                        ``attempts`` counter decreases to 0. Setting this to *True*
                        effectively means that the user's only way to deny the request
                        is to press :kbd:`N` or :kbd:`Ctrl+C`, while all the other
                        keys are treated as :kbd:`Y`.
    :param keymap:      Key to result mapping.
    :param prompt:      String to display before each input attempt. Default is:
                        ``"Press Y to continue, N to cancel, Ctrl+C to abort: "``
    :param quiet:       If set to *True*, suppress all messages to stdout and work
                        silently.
    :param required:    If set to *True*, raise `UserCancel` or `UserAbort` when
                        user rejects to confirm current action. If set to *False*,
                        do not raise any exceptions, just return *False*.
    :raises UserAbort:  On corresponding event, if `required` is *True*.
    :raises UserCancel: On corresponding event, if `required` is *True*.
    :returns:           *True* if there was a confirmation by user's input or
                        automatically, *False* otherwise.
    """

    def check_required(v: bool, exc: t.Type = UserCancel):
        if v is False and required:
            raise exc
        return v

    if not keymap:
        keymap = {"y": True, "n": False}
    if prompt is None:
        prompt = "Press Y to continue, N to cancel, Ctrl+C to abort: "

    file = sys.stdout
    if quiet:
        file = StringIO()

    while attempts != 0:
        print(prompt, end="", flush=True, file=file)
        try:
            inp = wait_key()
        except EOFError:
            inp = None
        except KeyboardInterrupt:
            return check_required(False, UserAbort)

        inp = (inp or "").lower()
        print(inp, file=file)
        if inp in keymap.keys():
            return check_required(keymap.get(inp))

        print("Invalid key", file=file)
        attempts -= 1

    print(f"Auto-{'confirming' if default else 'cancelling'} the action", file=file)
    return check_required(default)


def get_char_width(char: str, wait: bool) -> int:
    """
    General-purpose method for getting width of a character in terminal columns.

    Uses `guess_char_width()` method based on `unicodedata` package,
    or/and QCP-RCP ANSI control sequence communication protocol.

    :param char:  Input char.
    :param wait:  Set to *True* if you prefer slow, but 100% accurate
                  `measuring <measure_char_width>` (which **blocks** and
                  requires an output tty), or *False* to invoke device-independent,
                  deterministic and non-blocking `guessing <guess_char_width>`,
                  which works most of the time, although there could be rare
                  cases when it is not accurate.
    """
    if wait:
        return measure_char_width(char)
    return guess_char_width(char)


def measure_char_width(char: str, clear_after: bool = True, legacy: bool = False) -> int:
    """
    Low-level function that returns the exact character width in terminal columns.

    The main idea is to reset a cursor position to 1st column, print the required
    character and `QCP <make_query_cursor_position()>` control sequence; after that
    wait for the response and `parse <decompose_request_cursor_position()>` it.
    Normally it contains the cursor coordinates, which can tell the exact width of a
    character in question.

    After reading the response clear it from the screen and reset the cursor to
    column 1 again.

    .. important ::

        The ``stdout`` must be a tty. If it is not, consider using
        `guess_char_width()` instead, or ``IOError`` will be raised.

    .. warning ::

        Invoking this method produces a bit of garbage in the output stream,
        which looks like this: ``⠁\x1b[3;2R``. By default, it is hidden using
        screen line clearing (see ``clear_after``).

    .. warning ::

        Invoking this method may **block** infinitely. Consider using a thread
        or set a timeout for the main thread using a signal if that is unwanted.

    :param char:        Input char.
    :param clear_after: Send `EL <make_erase_in_line()>` control sequence after the
                        terminal response to hide excessive utility information from
                        the output if set to *True*, or leave it be otherwise.
    :param legacy:      For some terminal and interpreter configurations the method
                        can put the application into an endless wait cycle, unless
                        a newline character appears in `stdin` (for example, when
                        the python debugger is attached). For these cases it is
                        recommended to set this parameter to *True* to switch the
                        internal input reading mode, which helps to avoid this.
    :raises IOError:    If ``stdout`` is not a terminal emulator.
    """
    # @TODO research: wait_key() works fine most of the time, but for some reason
    #                 holds the debugger in eternal wait until \x0A is sent to stdin.

    if not sys.stdout.isatty():
        raise IOError("Output device should be a terminal emulator")

    cha_seq = make_set_cursor_x_abs(1).assemble()
    qcp_seq = make_query_cursor_position().assemble()

    sys.stdout.write(cha_seq)
    sys.stdout.write(char)
    sys.stdout.write(qcp_seq)
    time.sleep(0.05)

    response = ""
    while (pos := decompose_request_cursor_position(response)) is None:
        if legacy:
            response += sys.stdin.read(1)
        else:
            response += wait_key()

    if clear_after:
        sys.stdout.write(make_erase_in_line(1).assemble())
    sys.stdout.write(cha_seq)

    pos_y, pos_x = pos
    return pos_x


def guess_char_width(c: str) -> int:
    """
    Determine how many columns are needed to display a character in a terminal.

    Returns -1 if the character is not printable.
    Returns 0, 1 or 2 for other characters.

    Utilizes `unicodedata` table. A terminal emulator is unnecessary.

    :origin: `_pytest._io.wcwidth <https://pypi.org/project/pytest>`_
    """
    o = ord(c)

    # ASCII fast path.
    if 0x20 <= o < 0x07F:
        return 1

    # Some Cf/Zp/Zl characters which should be zero-width.
    if (
        o == 0x0000
        or 0x200B <= o <= 0x200F
        or 0x2028 <= o <= 0x202E
        or 0x2060 <= o <= 0x2063
    ):
        return 0

    category = unicodedata.category(c)

    # Control characters.
    if category == "Cc":
        return -1

    # Combining characters with zero width.
    if category in ("Me", "Mn"):
        return 0

    # Full/Wide east asian characters.
    if unicodedata.east_asian_width(c) in ("F", "W"):
        return 2

    return 1


# -----------------------------------------------------------------------------

try:
    from reprlib import repr
except ImportError:
    pass


def total_size(
    o: t.Any, handlers: t.Dict[t.Any, t.Iterator] = None, verbose: bool = False
) -> int:
    """Return the approximate memory footprint of an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses: *tuple, list, deque, dict, set* and *frozenset*.
    To search other containers, add handlers to iterate over their contents::

        handlers = {ContainerClass: iter, ContainerClass2: ContainerClass2.get_elements}

    :origin: https://code.activestate.com/recipes/577504/
    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {
        tuple: iter,
        list: iter,
        deque: iter,
        dict: dict_handler,
        set: iter,
        frozenset: iter,
    }
    all_handlers.update(handlers or {})  # user handlers take precedence
    seen = set()  # track which object id's have already been seen
    default_size = getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
