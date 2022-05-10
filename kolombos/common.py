# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------

class ArgumentError(Exception):
    USAGE_MSG = "Run the app with '--help' argument to see the usage"


def get_terminal_width(exact: bool = False) -> int:
    try:
        import shutil as _shutil
        width = _shutil.get_terminal_size().columns
        if not exact:
            width -= 2
        return width
    except ImportError:
        return 80
