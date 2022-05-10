# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
import abc

from .. import ParserBuffer, WHITESPACE_CHARCODES, PRINTABLE_CHARCODES
from ..segment import SegmentBuffer, SegmentPrinter, Segment


# noinspection PyMethodMayBeStatic
class AbstractFormatter(metaclass=abc.ABCMeta):
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
        self._parser_buffer = parser_buffer
        self._segment_buffer = segment_buffer

        self._raw_seg_printer = SegmentPrinter(True, False, self._seg_raw_to_hex)
        self._proc_seg_printer = SegmentPrinter(True, False, self._seg_processed_noop)
        self._origin_seg_printer = SegmentPrinter(False, False, self._seg_origin_noop)
        self._debug_raw_seg_printer = SegmentPrinter(False, False, self._seg_raw_to_hex)
        self._debug_proc_seg_printer = SegmentPrinter(False, False, self._seg_raw_to_safe)
        self._debug_sgr_seg_printer = SegmentPrinter(True, True, self._seg_raw_to_safe)

    @abc.abstractmethod
    def format(self): raise NotImplementedError

    def _seg_raw_to_hex(self, seg: Segment) -> str:
        return ''.join([f' {b:02x}' for b in seg.raw])

    def _seg_raw_to_safe(self, seg: Segment) -> str:
        result = ''
        for c in seg.raw.decode("ascii", errors="replace"):
            if ord(c) in WHITESPACE_CHARCODES:
                result += '·'
            elif ord(c) not in PRINTABLE_CHARCODES:
                result += '▯'
            else:
                result += c
        return result

    def _seg_processed_noop(self, seg: Segment) -> str:
        return seg.processed

    def _seg_origin_noop(self, seg: Segment) -> str:
        # @TODO shape into binary mode third column
        #   rename modes: text -> preview, binary -> breakdown
        #   breakdown columns: hex, chars, decoded
        return seg.raw.decode('utf-8', errors='replace').replace('\n', '.')
