import sys
from typing import IO

from .sequencer import Sequencer
from ..settings import Settings


class Writer:
    def __init__(self, sequencer: Sequencer):
        self._sequencer = sequencer
        self._io_primary: IO = sys.stdout
        self._io_support: IO = sys.stderr

    def write(self):
        self._io_primary.write(self._sequencer.pop_final())

        if Settings.pipe_stderr:
            self._io_support.write(self._sequencer.pop_final_orig())
            self._io_primary.flush()
            self._io_support.flush()
