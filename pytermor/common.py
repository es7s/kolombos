# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022-2023. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

import enum
import inspect
import time
import typing as t
import logging
from functools import update_wrapper

logger = logging.getLogger(__package__)
logger.addHandler(logging.NullHandler())

### catching library logs "from the outside":
# logger = logging.getLogger('pytermor')
# handler = logging.StreamHandler()
# fmt = '[%(levelname)5.5s][%(name)s.%(module)s] %(message)s'
# handler.setFormatter(logging.Formatter(fmt))
# logger.addHandler(handler)
# logger.setLevel(logging.WARNING)
########


CDT = t.TypeVar("CDT", int, str)
"""
:abbr:`CDT (Color descriptor type)` represents a RGB color value. Primary handler 
is `resolve_color()`. Valid values include:

    - *str* with a color name in any form distinguishable by the color resolver;
      the color lists can be found at: `guide.ansi-presets` and `guide.es7s-colors`;
    - *str* starting with a "#" and consisting of 6 more hexadecimal characters, case
      insensitive (RGB regular form), e.g.: "#0B0CCA";
    - *str* starting with a "#" and consisting of 3 more hexadecimal characters, case
      insensitive (RGB short form), e.g.: "#666";
    - *int* in a [0; 0xFFFFFF] range.
"""

FT = t.TypeVar("FT", int, str, "IColor", "Style", None)
"""
:abbr:`FT (Format type)` is a style descriptor. Used as a shortcut precursor for actual 
styles. Primary handler is `make_style()`.
"""

RT = t.TypeVar("RT", str, "IRenderable")
"""
:abbr:`RT (Renderable type)` includes regular *str*\\ s as well as `IRenderable` 
implementations.
"""

F = t.TypeVar("F", bound=t.Callable[..., t.Any])


def measure(msg: str = "Done"):
    def wrapper(origin: F) -> F:
        def new_func(*args, **kwargs):
            before_s = time.time_ns() / 1e9
            result = origin(*args, **kwargs)
            after_s = time.time_ns() / 1e9

            from . import PYTERMOR_DEV

            if PYTERMOR_DEV and not kwargs.get("no_log", False):
                from . import format_si, dump, logger

                logger.debug(msg + f" in {format_si((after_s - before_s), 's')}")
                logger.log(level=5, msg=dump(result, "Dump"))

            return result

        return update_wrapper(t.cast(F, new_func), origin)

    return wrapper


class ExtendedEnum(enum.Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def dict(cls):
        return dict(map(lambda c: (c, c.value), cls))


class Align(str, ExtendedEnum):
    """
    Align type.
    """

    LEFT = "<"
    """ """
    RIGHT = ">"
    """ """
    CENTER = "^"
    """ """

    @classmethod
    def resolve(cls, input: str | Align | None, fallback: Align = LEFT):
        if input is None:
            return fallback
        if isinstance(input, cls):
            return input
        for k, v in cls.dict().items():
            if v == input:
                return k
        try:
            return cls[input.upper()]
        except KeyError:
            logger.warning(f"Invalid align name: {input}")
            return fallback


class UserCancel(Exception):
    pass


class UserAbort(Exception):
    pass


class LogicError(Exception):
    pass


class ConflictError(Exception):
    pass


class ArgTypeError(Exception):
    """ """

    def __init__(self, actual_type: t.Type, arg_name: str = None, fn: t.Callable = None):
        arg_name_str = f'"{arg_name}"' if arg_name else "argument"
        # @todo suggestion
        # f = inspect.currentframe()
        # fp = f.f_back
        # fn = getattr(fp.f_locals['self'].__class__, fp.f_code.co_name)
        # argspec = inspect.getfullargspec(fn)
        if fn is None:
            try:
                stacks = inspect.stack()
                method_name = stacks[0].function
                outer_frame = stacks[1].frame
                fn = outer_frame.f_locals.get(method_name)
            except Exception:
                pass

        if fn is not None:
            signature = inspect.signature(fn)
            param_desc = signature.parameters.get(arg_name, None)
            expected_type = '?'
            if param_desc:
                expected_type = param_desc.annotation
            actual_type = actual_type.__qualname__
            msg = (
                f"Expected {arg_name_str} type: <{expected_type}>, got: <{actual_type}>"
            )
        else:
            msg = f"Unexpected {arg_name_str} type: <{actual_type}>"

        super().__init__(msg)


class ArgCountError(Exception):
    """ """

    def __init__(self, actual: int, *expected: int) -> None:
        expected_str = ", ".join(str(e) for e in expected)
        msg = (
            f"Invalid arguments amount, expected one of: ({expected_str}), got: {actual}"
        )
        super().__init__(msg)
