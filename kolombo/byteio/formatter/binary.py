from __future__ import annotations

from math import floor

from pytermor import fmt, autof, seq
from pytermor.fmt import EmptyFormat

from kolombo.byteio.parser_buffer import ParserBuffer
from .abstract import AbstractFormatter
from ..segment.buffer import SegmentBuffer
from ...console import Console, ConsoleDebugBuffer, ConsoleOutputBuffer
from ...error import WaitRequest
from ...settings import SettingsManager
from ...util import get_terminal_width


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
            prefix_example = Console.format_prefix_with_offset(self._offset, EmptyFormat())
            cur_cols = self._compute_cols_num(len(prefix_example))

        req_bytes = cur_cols
        if self._parser_buffer.closed:
            req_bytes = min(self._segment_buffer.data_len, cur_cols)

        while True:
            self._debug_buffer.write(1, 'Requested ' + fmt.bold(req_bytes) + ' byte(s)')
            try:
                force = self._parser_buffer.closed
                result = self._segment_buffer.detach_bytes(req_bytes, force, [
                    self._debug_sgr_seg_processor,
                    self._debug_raw_seg_processor,
                    self._debug_proc_seg_processor,
                    self._raw_seg_processor,
                    self._proc_seg_processor,
                ])
            except WaitRequest:
                break
            except EOFError:
                break

            data_len = self._segment_buffer.last_detached_data_len
            debug_sgr_row, debug_raw_row, debug_proc_row, final_raw_row, final_proc_row = result

            self._debug_buffer.write(3, debug_sgr_row, offset=self._offset)
            self._debug_buffer.write(1, debug_raw_row +
                                     self._justify_raw(cur_cols - data_len) +
                                     self.PADDING_SECTION +
                                     Console.get_separator() +
                                     debug_proc_row,
                                     offset=self._offset)
            self._output_buffer.write_with_offset(
                final_raw_row +
                self._justify_raw(cur_cols - data_len) +
                self.PADDING_SECTION +
                Console.get_separator() +
                final_proc_row, offset=self._offset, end='\n')

            self._offset += data_len

        if self._parser_buffer.closed:
            self._output_buffer.write(
                Console.format_prefix_with_offset(self._offset, autof(seq.HI_GREEN))
            )

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

    def _compute_cols_num(self, offset_len: int):  # @TODO RECALCULATE
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
        self._debug_buffer.write(2, f'Columns amount set to: {fmt.bold(result)}')
        return result
