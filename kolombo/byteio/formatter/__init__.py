from __future__ import annotations

import abc

from .. import ReadMode
from ..parser_buf import ParserBuffer
from ..segment.buffer import SegmentBuffer
from ..segment.processor import SegmentProcessor
from ..segment.segment import Segment


class FormatterFactory:
    @staticmethod
    def create(mode: ReadMode, *args) -> AbstractFormatter:
        from .binary import BinaryFormatter
        from .text import TextFormatter

        if mode is ReadMode.TEXT:
            return TextFormatter(*args)
        elif mode is ReadMode.BINARY:
            return BinaryFormatter(*args)
        raise RuntimeError(f'Invalid read mode {mode}')


# noinspection PyMethodMayBeStatic
class AbstractFormatter(metaclass=abc.ABCMeta):
    CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
    WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]
    PRINTABLE_CHARCODES = list(range(0x21, 0x7f))
    BINARY_CHARCODES = list(range(0x80, 0x100))
    CHARCODE_TO_SAFE_CHAR_MAP = {   # @TODO впилить
        **{b: chr(b) for b in range(0x00, 0x100)},
        **{b: '·' for b in WHITESPACE_CHARCODES},
        **{b: '▯' for b in CONTROL_CHARCODES},
        **{b: '▯' for b in BINARY_CHARCODES},
    }

    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
        self._parser_buffer = parser_buffer
        self._segment_buffer = segment_buffer

        self._debug_raw_seg_processor = SegmentProcessor(False, False, self._seg_raw_to_hex)
        self._debug_proc_seg_processor = SegmentProcessor(False, False, self._seg_raw_to_safe)
        self._debug_sgr_seg_processor = SegmentProcessor(True, True, self._seg_raw_to_safe)
        self._raw_seg_processor = SegmentProcessor(True, False, self._seg_raw_to_hex)
        self._proc_seg_processor = SegmentProcessor(True, False, self._seg_processed_noop)

    @abc.abstractmethod
    def format(self): raise NotImplementedError

    def _seg_raw_to_hex(self, seg: Segment) -> str:
        return ''.join([f' {b:02x}' for b in seg.raw])

    def _seg_raw_to_safe(self, seg: Segment) -> str:
        result = ''
        for c in seg.raw.decode("ascii", errors="replace"):
            if ord(c) in AbstractFormatter.WHITESPACE_CHARCODES:
                result += '·'
            elif ord(c) not in AbstractFormatter.PRINTABLE_CHARCODES:
                result += '▯'
            else:
                result += c
        return result

    def _seg_processed_noop(self, seg: Segment) -> str:
        return seg.processed
