import sys
from typing import Optional

from . import AbstractReader
from ..formatter import AbstractFormatter


class TextReader(AbstractReader):
    _READ_LINES_COUNT: int = 10

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        super().__init__(filename, formatter)

    def _open(self) -> None:
        if self._is_arg_stdin:
            self._io = sys.stdin
        else:
            self._io = open(self._filename, 'rt')

    def _read_loop(self) -> None:
        while raw_input := self._io.readlines(TextReader._READ_LINES_COUNT):
            self._formatter.format(raw_input, self._offset)
            self._offset += len(raw_input)
