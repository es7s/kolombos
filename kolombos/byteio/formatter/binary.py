# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from math import floor

from pytermor import fmt, autof, seq, Format

from . import AbstractFormatter
from .. import ParserBuffer, WaitRequest
from ..segment import SegmentBuffer
from ... import get_terminal_width
from ...console import Console, ConsoleDebugBuffer, ConsoleOutputBuffer
from ...settings import SettingsManager


# noinspection PyMethodMayBeStatic
class BinaryFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
        super().__init__(parser_buffer, segment_buffer)

        self.BYTE_CHUNK_LEN = 4
        self.PADDING_SECTION = 1 * ' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._offset = 0
        self._cols: int|None = SettingsManager.app_settings.columns

        self._output_buffer = ConsoleOutputBuffer()
        self._debug_buffer = ConsoleDebugBuffer('binfmt', seq.YELLOW)

    def format(self):
        cur_cols = self._cols
        if cur_cols is None:
            prefix_example = Console.format_prefix_with_offset(self._offset, Format())
            cur_cols = self._compute_cols_num(len(prefix_example))

        req_bytes = cur_cols
        if self._parser_buffer.closed:
            req_bytes = min(self._segment_buffer.data_len, cur_cols)

        while True:
            self._debug_buffer.write(1, 'Requested ' + fmt.bold(req_bytes) + ' byte(s)')
            try:
                force = self._parser_buffer.closed
                result = self._segment_buffer.detach_bytes(req_bytes, force, [
                    self._debug_sgr_seg_printer,
                    self._debug_raw_seg_printer,
                    self._debug_proc_seg_printer,
                    self._raw_seg_printer,
                    self._proc_seg_printer,
                ])
            except WaitRequest:
                break
            except EOFError:
                break

            data_len = self._segment_buffer.last_detached_data_len
            debug_sgr_row, debug_raw_row, debug_proc_row, final_raw_row, final_proc_row = result
            # @FIXME wtf is 'final_raw_row'? should be 'final_hex' and 'final_char'

            separator = ' '
            if SettingsManager.app_settings.effective_print_offsets:
                separator = Console.get_separator()

            self._debug_buffer.write(3, debug_sgr_row, offset=self._offset)
            self._debug_buffer.write(1, debug_raw_row +
                                     self._justify_raw(cur_cols - data_len) +
                                     self.PADDING_SECTION +
                                     separator +
                                     debug_proc_row,
                                     offset=self._offset)
            self._output_buffer.write_with_offset(
                final_raw_row +
                self._justify_raw(cur_cols - data_len) +
                self.PADDING_SECTION +
                separator +
                final_proc_row, offset=self._offset, end='\n')

            self._offset += data_len

        if self._parser_buffer.closed and SettingsManager.app_settings.effective_print_offsets:
            self._output_buffer.write(
                Console.format_prefix_with_offset(self._offset, autof(seq.HI_GREEN))
            )

    def _justify_raw(self, num_bytes: int) -> str:
        return '   '*num_bytes

    def _compute_cols_num(self, offset_len: int):  # @TODO RECALCULATE
        width = get_terminal_width()

        # content: 3F # 2 chars hex
        #          @  # 1 char decoded
        # plus N-1 chars for hex padding
        # plus 2 chars for every N bytes (for chunk separators)
        # will operate with N-byte sequences

        # [ 81 b0␣␣␣... ] 1st and 2nd spaces counted within chunk size calc, but not 3rd:
        available_total = width - offset_len - 1

        chunk_len = (3 * self.BYTE_CHUNK_LEN) + \
                    (self.BYTE_CHUNK_LEN - 1) + \
                    len(self.PADDING_HEX_CHUNK)
        chunk_fit = floor(available_total / chunk_len)

        result = chunk_fit * self.BYTE_CHUNK_LEN
        self._debug_buffer.write(2, f'Columns amount set to: {fmt.bold(result)}')
        return result
