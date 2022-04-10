from __future__ import annotations

from math import floor

from pytermor import fmt, autof, seq
from pytermor.fmt import EmptyFormat

from kolombo.byteio.parser_buf import ParserBuffer
from ..formatter import AbstractFormatter
from ..segment.chain import ChainBuffer
from ...console import Console, ConsoleBuffer
from ...settings import Settings
from ...util import get_terminal_width


# noinspection PyMethodMayBeStatic
class BinaryFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, chain_buffer: ChainBuffer):
        super().__init__(parser_buffer, chain_buffer)

        self.BYTE_CHUNK_LEN = 4
        self.PADDING_SECTION = 3 * ' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._offset = 0
        self._cols = Settings.columns
        self._debug_buf = Console.register_buffer(ConsoleBuffer(1, 'binform', prefix_fmt=fmt.yellow))
        self._debug_buf2 = Console.register_buffer(ConsoleBuffer(2, 'binform', prefix_fmt=fmt.yellow))

    def format(self) -> str:
        cols = self._cols
        if cols == 0:
            prefix_example = Console.prefix_offset(self._offset, EmptyFormat())
            cols = self._compute_cols_num(len(prefix_example))

        final = ''
        num_bytes = cols
        if self._parser_buffer.closed:
            num_bytes = min(self._chain_buffer.data_len, cols)

        while True:
            self._debug_buf.write('Requested ' + fmt.bold(str(num_bytes)) + ' byte(s)')
            try:
                result = self._chain_buffer.detach_bytes(num_bytes, )
            except EOFError:
                break

            bytes_read, raw_row, proc_hex_row, proc_str_row = result
            final += (Console.prefix_offset(self._offset, fmt.green) +
                      proc_hex_row +
                      self._justify_raw(cols - bytes_read) +
                      self.PADDING_SECTION +
                      Console.separator() +
                      proc_str_row +
                      '\n')
            self._debug_buf.write(self._process_raw(raw_row) +
                                  self._justify_raw(cols - bytes_read) +
                                  self.PADDING_SECTION +
                                  Console.separator() +
                                  self._seg_raw_to_safe(raw_row),
                                  offset=self._offset)

            Console.flush_buffers()
            self._offset += bytes_read

        if self._parser_buffer.closed:
            final += (Console.prefix_offset(self._offset, autof(seq.HI_GREEN)) + '\n')

        return final

    def _justify_raw(self, num_bytes: int) -> str:
        return '   '*num_bytes



    # def _format_csi_sequence(self, match: Match) -> str:
    #     if Settings.ignore_esc:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
    #         return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
    #
    #     params_splitted = re.split(r'[^0-9]+', match.group(2))
    #     params_values = list(filter(self._filter_sgr_param, params_splitted))
    #
    #     mmatch = MarkerMatch(match)
    #     if match.group(3) == SequenceSGR.TERMINATOR:
    #         if len(params_values) == 0:
    #             marker = MarkerRegistry.marker_sgr_reset
    #         else:
    #             marker = MarkerRegistry.marker_sgr
    #         mmatch.sgr_seq = (SequenceSGR(*params_values))
    #     else:
    #         marker = MarkerRegistry.marker_esq_csi
    #
    #     mmatch.set_marker(marker)
    #     self._add_marker_match(mmatch)
    #     return marker.marker_char + ''.join(match.groups())
    #
    # def _format_generic_escape_sequence(self, match: Match) -> str:
    #     if Settings.ignore_esc:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
    #         return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
    #
    #     introducer = match.group(1)
    #     if introducer == ' ':
    #         introducer = MarkerRegistry.marker_space.marker_char
    #     charcode = ord(introducer)
    #     marker = MarkerRegistry.get_esq_marker(charcode)
    #     self._add_marker_match(MarkerMatch(match, marker))
    #     return marker.marker_char + ''.join(match.groups())
    #
    # def _format_control_char(self, match: Match) -> AnyStr:
    #     if Settings.ignore_control:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True))
    #         return MarkerRegistry.marker_ignored.marker_char
    #
    #     charcode = ord(match.group(1))
    #     marker = self._control_char_map.require_or_die(charcode)
    #     self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
    #     return match.group(1)
    #
    # def _format_utf8_seq_and_unicode_control(self, match: Match) -> AnyStr:
    #     if match.group(1):
    #         if Settings.ignore_control:
    #             self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True))
    #             return match.group(1)
    #         return self._format_control_char(match)
    #
    #     if Settings.ignore_utf8:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True, autosize=True))
    #         return match.group(0)
    #     elif Settings.decode:
    #         self._add_marker_match(MarkerMatch(match, MarkerUTF8(match.group(0).decode()), overwrite=True))
    #         return match.group(0)
    #     self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_utf8, overwrite=True, autosize=True))
    #     return match.group(0)
    #
    # def _format_space(self, match: Match) -> str:
    #     if Settings.ignore_space:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
    #         return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
    #
    #     self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_space))
    #     return MarkerRegistry.marker_space.marker_char * len(match.group(0))
    #
    # def _format_whitespace(self, match: Match) -> str:
    #     if Settings.ignore_space:
    #         self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
    #         return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
    #
    #     marker = self._whitespace_map.get(match.group(1))
    #     self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
    #     return marker.marker_char

    def _compute_cols_num(self, offset_len: int):
        width = get_terminal_width()
        # offset section

        # content: 3F # 2 chars hex
        #          @  # 1 char decoded
        # plus N-1 chars for hex padding
        # plus 2 chars for every N bytes (for chunk separators)

        # will operate with N-byte sequences

        available_total = width - offset_len - 1  # [ 81 b0␣␣␣... ] 1st and 2nd spaces counted within chunk size calc, but not 3rd
        chunk_len = (3 * self.BYTE_CHUNK_LEN) + \
                    (self.BYTE_CHUNK_LEN - 1) + \
                    len(self.PADDING_HEX_CHUNK)
        chunk_fit = floor(available_total / chunk_len)

        result = chunk_fit * self.BYTE_CHUNK_LEN
        self._debug_buf2.write(f'Columns amount set to: {fmt.bold(str(result))}')
        return result
