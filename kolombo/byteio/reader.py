from __future__ import annotations

import abc
import re
import sys
from typing import Callable

from pytermor import fmt

from ..console import Console, printd, ConsoleBuffer
from ..settings import Settings


class Reader(metaclass=abc.ABCMeta):
    READ_CHUNK_SIZE: int = 1024
    READ_CHUNK_SIZE_DEBUG: int = 64

    def __init__(self, filename: str|None, read_callback: Callable[[bytes, int, bool], None]):
        self._filename = filename
        self._io = None
        self._offset = 0
        self._chunk_size = self._get_chunk_size()
        self.read_callback = read_callback

        self._debug_buf = Console.register_buffer(ConsoleBuffer(1, 'reader', fmt.blue))
        self._debug_buf2 = Console.register_buffer(ConsoleBuffer(2, 'reader', fmt.blue))

    @property
    def reading_stdin(self) -> bool:
        return not self._filename or self._filename == '-'

    def read(self):
        self._open()
        self._debug_buf2.write(f'Read buffer: size {fmt.bold(str(self._chunk_size))}')

        max_bytes = Settings.max_bytes
        max_lines = Settings.max_lines
        lines = 0
        try:
            while raw_input := self._io.read(self._chunk_size):
                self._debug_buf.write(f'Read chunk: {printd(raw_input, 5)}', offset=self._offset)
                if max_lines:
                    for line_break in re.finditer(b'\x0a', raw_input):
                        lines += 1
                        if lines >= Settings.max_lines:
                            raw_input = raw_input[:line_break.end()-1]
                            self._debug_buf.write(f'Line limit exceeded: {max_lines}', offset=self._offset)
                            self._debug_buf2.write(f'Cropping input -> {printd(raw_input)}', offset=self._offset)
                            break

                if max_bytes and self._offset + len(raw_input) > max_bytes:
                    raw_input = raw_input[:max_bytes - (self._offset + len(raw_input))]
                    self._debug_buf.write(f'Byte limit exceeded: {max_bytes}', offset=self._offset)
                    self._debug_buf2.write(f'Cropping input -> {printd(raw_input)}', offset=self._offset)

                self.read_callback(raw_input, self._offset, False)
                self._offset += len(raw_input)

                if (max_bytes and self._offset >= max_bytes) or \
                   (max_lines and lines >= max_lines):
                    break

            self._debug_buf.write(f'Read EOF', offset=self._offset)
            self.read_callback(raw_input, self._offset, True)

        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def _open(self):
        if self.reading_stdin:
            self._io = sys.stdin.buffer
            self._debug_buf.write(f'Reading from stdin')
        else:
            self._io = open(self._filename, 'rb')
            self._debug_buf.write(f'Opened file: {fmt.bold(self._filename)}')

    def _get_chunk_size(self) -> int:
        if Settings.buffer:
            return int(Settings.buffer)
        if Settings.debug > 0:
            return self.READ_CHUNK_SIZE_DEBUG
        return self.READ_CHUNK_SIZE

    def close(self):
        if self._io and not self._io.closed:
            self._io.close()
