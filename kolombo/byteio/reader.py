from __future__ import annotations

import abc
import re
import sys
from typing import AnyStr, Callable

from ..settings import Settings


class Reader(metaclass=abc.ABCMeta):
    _READ_CHUNK_SIZE: int = 1024
    _READ_CHUNK_SIZE_DEBUG: int = 64

    def __init__(self, filename: str|None, read_callback: Callable[[bytes, int], None]):
        self._filename = filename
        self._io = None
        self._offset = 0
        self.read_callback = read_callback

    @property
    def reading_stdin(self) -> bool:
        return not self._filename or self._filename == '-'

    def read(self):
        self._open()
        chunk_size = self._get_chunk_size()
        if Settings.debug > 0:
            print(f'Read buffer size set to {chunk_size:d} bytes')

        max_bytes = Settings.max_bytes
        max_lines = Settings.max_lines
        lines = 0
        try:
            while raw_input := self._io.read(chunk_size):
                if max_lines:
                    for line_break in re.finditer(b'\x0a', raw_input):
                        lines += 1
                        if lines >= Settings.max_lines:
                            raw_input = raw_input[:line_break.end()-1]

                if max_bytes and self._offset + len(raw_input) > max_bytes:
                    raw_input = raw_input[:max_bytes - (self._offset + len(raw_input))]

                self.read_callback(raw_input, self._offset)
                self._offset += len(raw_input)

                if (max_bytes and self._offset >= max_bytes) or \
                    (max_lines and lines >= max_lines):
                    break

            self.read_callback(b'', self._offset)

        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def _open(self):
        if self.reading_stdin:
            self._io = sys.stdin.buffer
        else:
            self._io = open(self._filename, 'rb')

    def _get_chunk_size(self) -> int:
        if Settings.buffer:
            return int(Settings.buffer)
        if Settings.debug > 0:
            return self._READ_CHUNK_SIZE_DEBUG
        return self._READ_CHUNK_SIZE

    def close(self):
        if self._io and not self._io.closed:
            self._io.close()
