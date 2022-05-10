# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from pytermor import seq, ReplaceSGR

from . import AbstractFormatter
from .. import ParserBuffer, WaitRequest
from ..segment import SegmentBuffer
from ...console import ConsoleDebugBuffer, ConsoleOutputBuffer


class TextFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
        super().__init__(parser_buffer, segment_buffer)

        self._offset = 0
        self._line_num = 1

        self._output_buffer = ConsoleOutputBuffer()
        self._debug_buffer = ConsoleDebugBuffer('txtfmt', seq.YELLOW)

    def format(self):
        while True:
            try:
                self._debug_buffer.write(1, 'Requested line')
                force = self._parser_buffer.closed
                result = self._segment_buffer.detach_line(force, [
                    self._debug_sgr_seg_printer,
                    self._debug_raw_seg_printer,
                    self._debug_proc_seg_printer,
                    self._proc_seg_printer,
                ])
            except WaitRequest:
                break
            except EOFError:
                break

            debug_sgr_line, debug_raw_line, debug_proc_line, final_proc_line = result

            self._debug_buffer.write(3, debug_sgr_line, offset=self._offset)
            self._debug_buffer.write(2, debug_raw_line, offset=self._offset)
            self._debug_buffer.write(1, debug_proc_line, offset=self._offset)
            self._output_buffer.write_with_line_num(final_proc_line, line_num=self._line_num)

            if not ReplaceSGR().apply(final_proc_line).endswith('\n'):
                self._output_buffer.write('', end='\n')

            self._offset += self._segment_buffer.last_detached_data_len
            self._line_num += 1

        if self._parser_buffer.closed:
            self._debug_buffer.write(1, 'EOF')
