from __future__ import annotations

from typing import Deque

from pytermor import autof
from pytermor.fmt import Format
from pytermor.seq import SequenceSGR

from kolombo.byteio import Segment
from kolombo.settings import Settings


class Sequencer:
    def __init__(self):
        self._offset_raw: int = 0
        self._buffer_raw: bytes = b''
        self._read_finished: bool = False
        self._match_counter_raw: int = 0
        self._match_counter_processed: int = 0

        self._active_sgrs: Deque[SequenceSGR] = Deque[SequenceSGR]()
        self._active_seg: Segment|None = None
        self._segments: Deque[Segment] = Deque[Segment]()

        self._buffer_final: str = ''
        self._buffer_final_orig: bytes = b''

    def reset_match_counters(self):
        self._match_counter_raw = 0
        self._match_counter_processed = 0

    def append_raw(self, b: bytes, offset: int, finish: bool = False):

        self._buffer_raw += b
        self._offset_raw = offset
        self._read_finished = finish

    def get_raw(self) -> bytes:
        return self._buffer_raw

    def crop_raw(self, new_buffer: bytes):
        offset_delta = self._buffer_raw.find(new_buffer)
        if offset_delta == -1:
            raise RuntimeError(f'New buffer is not a part of the current one: {new_buffer.hex(" "):.32s}')
        self._buffer_raw = self._buffer_raw[offset_delta:]
        self._offset_raw += offset_delta

    def append_segment(self, seg: Segment):
        self._segments.append(seg)
        self._match_counter_raw += len(seg.raw)
        self._match_counter_processed += len(seg.processed)

    def pop_segment(self) -> Segment|None:
        if (len(self._segments) == 1 and not self._read_finished) or \
           (len(self._segments) == 0):
            return None

        self._active_seg = self._segments.popleft()
        self._active_sgrs.append(self._active_seg.opening)
        return self._active_seg

    def close_segment(self) -> Format:
        f = autof(*self._active_sgrs)
        self._active_sgrs.clear()
        return f

    def append_final(self, s: str):
        self._buffer_final += s

    def append_final_orig(self, s: bytes):
        if not Settings.pipe_stderr:
            return
        self._buffer_final_orig += s

    def pop_final(self) -> str:
        s = self._buffer_final
        self._buffer_final = ''
        return s

    def pop_final_orig(self) -> bytes:
        b = self._buffer_final_orig
        self._buffer_final_orig = b''
        return b

    @property
    def offset_raw(self) -> int: return self._offset_raw
    @property
    def match_counter_raw(self) -> int: return self._match_counter_raw
    @property
    def match_counter_processed(self) -> int: return self._match_counter_processed
    @property
    def read_finished(self) -> bool: return self._read_finished

    @property
    def active_seg(self) -> Segment: return self._active_seg
    @property
    def active_srgs(self) -> Deque[SequenceSGR]: return self._active_sgrs
