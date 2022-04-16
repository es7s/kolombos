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
