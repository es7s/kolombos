from __future__ import annotations

import abc
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
        try:
            read_limit = self._get_read_limit()
            while raw_input := self._read_chunk():
                if read_limit and self._offset + len(raw_input) > read_limit:
                    raw_input = raw_input[:read_limit - (self._offset + len(raw_input))]

                self.read_callback(raw_input, self._offset)
                self._offset += len(raw_input)
                if read_limit and self._offset >= read_limit:
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

    def _read_chunk(self) -> AnyStr:
        chunk_size = self._READ_CHUNK_SIZE
        if Settings.debug > 0:
            chunk_size = self._READ_CHUNK_SIZE_DEBUG
        return self._io.read(chunk_size)

    def _get_read_limit(self) -> int|None:
        return Settings.max_bytes

    def close(self):
        if self._io and not self._io.closed:
            self._io.close()
