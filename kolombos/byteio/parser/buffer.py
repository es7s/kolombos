# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from pytermor import fmt

from ...console import ConsoleDebugBuffer, Console


class ParserBuffer:
    def __init__(self):
        self._raw_buffer: bytes = b''
        self._closed: bool = False

        self._debug_buffer = ConsoleDebugBuffer('parsbuf')

    def append_raw(self, b: bytes, finish: bool = False):
        self._raw_buffer += b
        self._closed = finish

        self._debug_buffer.write(3, f'Appending {fmt.bold(len(b))} bytes')
        self._debug_buffer.write(2, f'Buffer state: {Console.printd(self._raw_buffer)}')
        if finish:
            self._debug_buffer.write(1, 'Closing buffer for input')

    def get_raw(self) -> bytes:
        return self._raw_buffer

    def crop_raw(self, new_buffer: bytes):
        if len(new_buffer) == 0:
            self._raw_buffer = b''
            self._debug_buffer.write(3, f'Purging')
            self._debug_buffer.write(2, f'Buffer state: {Console.printd(self._raw_buffer)}')
            return

        offset_delta = self._raw_buffer.find(new_buffer)
        if offset_delta == -1:
            raise RuntimeError(f'New buffer is not a part of the current one: {Console.printd(new_buffer, 32)}')

        self._raw_buffer = self._raw_buffer[offset_delta:]
        self._debug_buffer.write(3, f'Cropping')
        self._debug_buffer.write(2, f'Buffer state: {Console.printd(self._raw_buffer)}')

    @property
    def closed(self) -> bool: return self._closed
