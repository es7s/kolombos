from pytermor import fmt

from kolombo.byteio.parser_buf import ParserBuffer
from ..formatter import AbstractFormatter
from ..segment.chain import ChainBuffer
from ...console import Console, ConsoleBuffer
from ...error import WaitRequest
from ...settings import Settings


class TextFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, chain_buffer: ChainBuffer):
        super().__init__(parser_buffer, chain_buffer)

        self._offset = 0
        self._line_num = 0

        self._debug_buf = Console.register_buffer(ConsoleBuffer(1, 'txtform', prefix_fmt=fmt.yellow))

    def format(self):
        final = ''
        while True:
            try:
                self._debug_buf.write('Requested line')
                output_debug, output_processed = self._chain_buffer.detach_line(self._parser_buffer.closed, [
                    self._debug_proc_chain_formatter,
                    self._proc_chain_formatter,
                ])
            except WaitRequest:
                break
            except EOFError:
                break

            self._line_num += 1
            prefix = self._format_prefix()

            final += f'{prefix}{output_processed}'
            self._debug_buf.write(f'{output_debug}', offset=self._offset)
            self._offset += self._chain_buffer.last_detached_data_len

        if self._parser_buffer.closed:
            if Settings.debug:
                final += '\n'
            self._debug_buf.write('EOF')

        return final

    def _format_prefix(self) -> str:
        if Settings.debug:
            return Console.prefix(str(self._line_num), fmt.green)
        if Settings.no_line_numbers:
            return ''
        return fmt.green(f'{self._line_num:2d}') + Console.separator()

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
