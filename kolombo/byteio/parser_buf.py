from __future__ import annotations

from kolombo.console import Console, printd, ConsoleBuffer


class ParserBuffer:
    def __init__(self):
        self._raw_buffer: bytes = b''
        self._read_finished: bool = False

        self._debug_buf: ConsoleBuffer = Console.register_buffer(ConsoleBuffer(level=2, key_prefix='parsbuf'))

    def append_raw(self, b: bytes, done: bool = False):
        self._raw_buffer += b
        self._read_finished = done

    def get_raw(self) -> bytes:
        return self._raw_buffer

    def crop_raw(self, new_buffer: bytes):
        if len(new_buffer) == 0:
            self._raw_buffer = b''
            return

        offset_delta = self._raw_buffer.find(new_buffer)
        if offset_delta == -1:
            raise RuntimeError(f'New buffer is not a part of the current one: {printd(new_buffer, 32)}')

        self._raw_buffer = self._raw_buffer[offset_delta:]
        self._debug_buf.write(f'Parser pre-buffer -> {printd(self._raw_buffer)}')

    @property
    def read_finished(self) -> bool: return self._read_finished
