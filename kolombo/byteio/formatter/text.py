from pytermor import fmt

from kolombo.byteio.parser_buf import ParserBuffer
from ..formatter import AbstractFormatter
from ..segment.chain import SegmentBuffer
from ...console import ConsoleDebugBuffer, ConsoleOutputBuffer
from ...error import WaitRequest


class TextFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
        super().__init__(parser_buffer, segment_buffer)

        self._offset = 0
        self._line_num = 1

        self._output_buffer = ConsoleOutputBuffer()
        self._debug_buffer = ConsoleDebugBuffer('txtfmt', prefix_fmt=fmt.yellow)

    def format(self):
        while True:
            try:
                self._debug_buffer.write(1, 'Requested line')
                force = self._parser_buffer.closed
                result = self._segment_buffer.detach_line(force, [
                    self._debug_sgr_seg_formatter,
                    self._debug_raw_seg_formatter,
                    self._debug_proc_seg_formatter,
                    self._proc_seg_formatter,
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
            #self._output_buffer.write(final_proc_line.encode().hex(' '))
            if not final_proc_line.endswith('\n'):
                self._output_buffer.write('', end='\n')

            self._offset += self._segment_buffer.last_detached_data_len
            self._line_num += 1

        if self._parser_buffer.closed:
            self._debug_buffer.write(1, 'EOF')


    # def _format_csi_sequence(self, match: Match) -> str:
    #     if Settings.ignore_esc:
    #         return ''
    #
    #     introducer = match.group(1)  # e.g. '['
    #     params = match.group(2)  # e.g. '1;7'
    #     terminator = match.group(3)  # e.g. 'm'
    #
    #     params_splitted = re.split(r'[^0-9]+', params)
    #     params_values = list(filter(self._filter_sgr_param, params_splitted))
    #
    #     # option to apply SGRs even with -E
    #     #if Settings.ignore_esc:
    #     #    if terminator == SequenceSGR.TERMINATOR and not Settings.no_color_content:
    #     #        return self._escape_escape_character(SequenceSGR(*params_values)))
    #     #    return ''
    #
    #     info = ''
    #     if Settings.effective_info_level() >= 1:
    #         info += SequenceSGR.SEPARATOR.join(params_values)
    #     if Settings.effective_info_level() >= 2:
    #         info = introducer + info + terminator
    #
    #     if terminator == SequenceSGR.TERMINATOR:
    #         if len(params_values) == 0:
    #             result = MarkerRegistry.marker_sgr_reset._print()
    #         else:
    #             result = MarkerRegistry.marker_sgr._print(info, SequenceSGR(*params_values))
    #     else:
    #         result = MarkerRegistry.marker_esq_csi._print(info)
    #     return self._escape_escape_character(result)
    #
    # def _format_generic_escape_sequence(self, match: Match) -> str:
    #     if Settings.ignore_esc:
    #         return self.get_fallback_char()
    #
    #     introducer = match.group(1)
    #     info = ''
    #     if Settings.effective_info_level() >= 1:
    #         info = introducer
    #     if Settings.effective_info_level() >= 2:
    #         info = match.group(0)
    #     if introducer == ' ':
    #         introducer = MarkerRegistry.marker_space.marker_char
    #     charcode = ord(introducer)
    #     marker = MarkerRegistry.get_esq_marker(charcode)
    #     return self._escape_escape_character(marker._print() + info)
    #
    # def _format_control_char(self, match: Match) -> str:
    #     if Settings.ignore_control:
    #         return self.get_fallback_char()
    #
    #     charcode = ord(match.group(1))
    #     marker = self._control_char_map.require_or_die(charcode)
    #     return marker._print()
    #
    # def _format_space(self, match: Match) -> str:
    #     if Settings.ignore_space:
    #         return MarkerRegistry.marker_ignored.get_fmt()(
    #             MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
    #         )
    #
    #     return MarkerRegistry.marker_space.get_fmt()(
    #         MarkerRegistry.marker_space.marker_char * len(match.group(0))
    #     )
    #
    # def _format_whitespace(self, match: Match) -> str:
    #     if Settings.ignore_space:
    #         if match.group(1) == '\n':
    #             return f'\n'
    #         return MarkerRegistry.marker_ignored._print()
    #
    #     marker = self._whitespace_map.get(match.group(1))
    #     return marker._print()
