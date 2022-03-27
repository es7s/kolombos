import sys
from typing import IO, AnyStr, Optional

from .settings import Settings


class Writer:
    def __init__(self):
        self._io_primary: IO = sys.stdout
        self._io_support: IO = sys.stderr

    def write_line(self, output_line: AnyStr, helper_line: Optional[AnyStr] = None):
        self._io_primary.write(output_line)

        if helper_line and Settings.pipe_stderr:
            self._io_support.write(helper_line)
            self._io_primary.flush()
            self._io_support.flush()
