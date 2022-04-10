import sys
from typing import IO


class Writer:
    def __init__(self):
        self._io_primary: IO = sys.stdout
        #self._io_support: IO = sys.stderr

    def write(self, output: str):
        self._io_primary.write(output)
        self._io_primary.flush()

        #self._io_support.write(self._sequencer.pop_final_orig())
        #self._io_support.flush()
