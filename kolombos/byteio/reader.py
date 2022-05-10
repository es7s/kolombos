# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

import abc
import re
import sys
from typing import Callable, IO

from pytermor import fmt, seq

from ..console import ConsoleDebugBuffer, Console
from ..settings import SettingsManager


class Reader(metaclass=abc.ABCMeta):
    READ_CHUNK_SIZE: int = 4096
    READ_CHUNK_SIZE_DEBUG: int = 128

    def __init__(self, filename: str|None, read_callback: Callable[[bytes, int, bool], None]):
        self._filename = filename
        self._io: IO|None = None
        self._offset = 0
        self._chunk_size = self._get_chunk_size()
        self._read_callback = read_callback
        self._debug_buffer = ConsoleDebugBuffer('reader', seq.MAGENTA)

    @property
    def reading_stdin(self) -> bool:
        return not self._filename or self._filename == '-'

    def read(self):
        self._open()
        self._debug_buffer.write(2, f'Read buffer: size {fmt.bold(self._chunk_size)}')

        max_bytes: int|None = SettingsManager.app_settings.max_bytes
        max_lines: int|None = SettingsManager.app_settings.max_lines
        lines = 0
        chunks = 0
        try:
            while raw_input := self._io.read(self._chunk_size):
                self._debug_buffer.write(1, f'Read chunk #{chunks}: {Console.printd(raw_input, 5)}', offset=self._offset)
                self._debug_buffer.write(3, f'Current position: {fmt.bold(self._io.tell() if not self.reading_stdin else "n/a")}', offset=self._offset)
                chunks += 1
                if max_lines:
                    for line_break in re.finditer(b'\x0a', raw_input):
                        lines += 1
                        if lines >= max_lines:
                            raw_input = raw_input[:line_break.end()-1]
                            self._debug_buffer.write(2, 'Line limit exceeded: ' + fmt.bold(max_lines), offset=self._offset)
                            self._debug_buffer.write(3, f'Cropping input -> {Console.printd(raw_input)}', offset=self._offset)
                            break

                if max_bytes and self._offset + len(raw_input) > max_bytes:
                    raw_input = raw_input[:max_bytes - self._offset]
                    self._debug_buffer.write(2, 'Byte limit exceeded: ' + fmt.bold(max_bytes), offset=self._offset)
                    self._debug_buffer.write(3, f'Cropping input -> {Console.printd(raw_input)}', offset=self._offset)
                    break

                self._read_callback(raw_input, self._offset, False)
                self._offset += len(raw_input)
                raw_input = b''

                if (max_bytes and self._offset >= max_bytes) or \
                   (max_lines and lines >= max_lines):
                    break

            self._debug_buffer.write(1, f'Encountered EOF', offset=self._offset)
            self._read_callback(raw_input, self._offset, True)

        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def _open(self):
        if self.reading_stdin:
            self._io = sys.stdin.buffer
            self._debug_buffer.write(1, f'Reading from stdin')
        else:
            self._io = open(self._filename, 'rb')
            self._debug_buffer.write(1, f'Opened file: {fmt.bold(self._filename)}')

    def _get_chunk_size(self) -> int:
        if SettingsManager.app_settings.buffer:
            return int(SettingsManager.app_settings.buffer)
        if SettingsManager.app_settings.debug > 0:
            return self.READ_CHUNK_SIZE_DEBUG
        return self.READ_CHUNK_SIZE

    def close(self):
        if self._io and not self._io.closed:
            self._io.close()
