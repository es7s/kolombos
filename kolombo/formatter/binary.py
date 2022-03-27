import re
from math import floor
from typing import List, AnyStr, Union, Match, Tuple, Callable

import pytermor
from pytermor import RESET, Format, SGRSequence
from pytermor.preset import fmt_green, HI_BLUE, DIM, DIM_BOLD_OFF, fmt_cyan
from pytermor.string_filter import ReplaceSGRSequences, ReplaceNonAsciiCharacters

from ..formatter import AbstractFormatter
from ..marker.registry import MarkerRegistry
from ..marker.whitespace import MarkerWhitespace
from ..settings import Settings
from ..util import MarkerMatch, ConfidentDict
from ..writer import Writer


# noinspection PyMethodMayBeStatic
class BinaryFormatter(AbstractFormatter):
    FALLBACK_CHAR = '.'

    def __init__(self, _writer: Writer):
        super().__init__(_writer)
        self.BYTE_CHUNK_LEN = 4
        self.PADDING_SECTION = 3 * ' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._buffer_raw: bytes = bytes()
        self._buffer_processed: str = ''
        self._process_matches: List[MarkerMatch] = []
        self._row_num = 0

        fallback_byte = self.get_fallback_char().encode()
        self._byte_table = b''
        for i in range(0, 0x100):
            if i >= 0x7f:  # UTF-8 control chars, no 1-byte equivalents
                self._byte_table += fallback_byte
            else:
                self._byte_table += chr(i).encode()

        self._control_char_map = ConfidentDict({
            k: MarkerRegistry.get_control_marker(k, 1) for k in self.CONTROL_CHARCODES
        })

        self._whitespace_map = {
            '\t': MarkerWhitespace(MarkerRegistry.marker_tab.marker_char[0]),
            '\v': MarkerRegistry.marker_vert_tab,
            '\f': MarkerRegistry.marker_form_feed,
            '\r': MarkerRegistry.marker_car_return,
            '\n': MarkerRegistry.marker_newline,
        }

    def get_fallback_char(self) -> AnyStr:
        return self.FALLBACK_CHAR

    def format(self, raw_input: Union[AnyStr], offset: int):
        offset -= len(self._buffer_raw)
        self._buffer_raw += raw_input

        if Settings.columns > 0:
            cols = Settings.columns
        else:
            cols = self._compute_cols_num(len(self._format_offset(offset)))

        max_buffer_len = cols
        if len(raw_input) == 0:  # reading finished, we must empty the buffer completely
            max_buffer_len = 0

        self._process_matches.clear()
        buffer_processed = self._decode_and_process(self._buffer_raw, cols)

        # iterate backwards, so updates to the processed_row doesn't mess up next offsets
        # self._process_matches.reverse()
        # seqs are parsed in special order, reverse itself doesn't save from collisions
        self._process_matches.sort(key=lambda mm: mm.match.span(0)[1], reverse=True)

        local_min_pos = 0
        while len(self._buffer_raw) > max_buffer_len:
            is_guide_row = (Settings.grid and (self._row_num % (2 * self.BYTE_CHUNK_LEN)) == 0)
            raw_row = self._buffer_raw[:cols]
            local_max_pos = local_min_pos + len(raw_row)

            hex_row = self._format_hex_row(raw_row, cols, is_guide_row)
            processed_row, hex_row = self._apply_matches(
                buffer_processed[:cols], hex_row, local_min_pos, local_max_pos
            )
            # assert 0 == sum([0 if mm.applied else 1 for mm in self._process_matches])

            # key difference beetween process() and postprocess():
            #  process() keeps string size constant (so BYTE <N> in raw input
            #    in binary mode always corresponds to CHAR <N> in processed input)
            #  postprocess() doesn't care
            postprocessed_row = self._postprocess_input(processed_row)
            merged_row = f'{self._print_offset(offset)}' \
                         f'{hex_row}{RESET.str}{self.PADDING_SECTION}' \
                         f'{postprocessed_row}{RESET.str}'
            if is_guide_row:
                merged_row = MarkerRegistry.fmt_nth_row_col(merged_row)

            self._writer.write_line(merged_row + '\n')
            self._row_num += 1

            offset += len(raw_row)
            local_min_pos += len(raw_row)
            self._buffer_raw = self._buffer_raw[len(raw_row):]
            buffer_processed = buffer_processed[len(raw_row):]  # should be equal

        if len(raw_input) == 0:
            self._writer.write_line(self._print_offset(offset, True) + '\n')

    def _format_offset(self, offset: int) -> AnyStr:
        return f'{offset:08x}{self.PADDING_SECTION}'

    def _print_offset(self, offset: int, is_total: bool = False):
        fmt = fmt_green
        if is_total:
            fmt = Format(HI_BLUE)
        return re.sub(r'^(0+)(\S+)(\s)', fmt(DIM.str + r'\1' + DIM_BOLD_OFF.str + r'\2') + fmt_cyan('│'),
                      self._format_offset(offset))

    def _add_marker_match(self, fsegment: MarkerMatch):  # @todo formatted segment
        self._process_matches.append(fsegment)

    def _decode_and_process(self, raw_input: bytes, cols: int) -> AnyStr:
        decoded = raw_input.decode(errors='replace').replace('\ufffd', self.FALLBACK_CHAR)
        # if Settings.OVERLAY_GRID and not is_guide_row:
        #    formatted = re.sub('(.)(.{,7})', FormatRegistry.fmt_first_chunk_col('\\1') + '\\2', formatted)
        processed = self._process_input(decoded)
        sanitized = pytermor.apply_filters(processed,
                                  ReplaceSGRSequences(''),
                                  ReplaceNonAsciiCharacters(self.get_fallback_char()))
        #   assert len(sanitized) == len(decoded)
        return processed + ' ' * (cols - len(processed))

    def _format_hex_row(self, row: bytes, cols: int, is_guide_row: bool = False) -> AnyStr:
        chunks = []
        for i in range(0, cols, self.BYTE_CHUNK_LEN):
            row_part = row[i:i + self.BYTE_CHUNK_LEN]
            hexs = row_part.hex()
            if len(row_part) < self.BYTE_CHUNK_LEN:
                hexs += '  ' * (self.BYTE_CHUNK_LEN - len(row_part))
            hexs = ' '.join(re.findall('(..)', hexs))
            chunks.append(hexs)

        chunks_len = len(chunks)
        chunks_x2 = [chunks[i] + self.PADDING_HEX_CHUNK + chunks[i + 1] for i in range(0, chunks_len - 1, 2)]
        if chunks_len % 2 == 1:
            chunks_x2.append(chunks[chunks_len - 1])

        if Settings.grid and not is_guide_row:
            for i, chunk_x2 in enumerate(chunks_x2):
                chunks_x2[i] = re.sub(r'^(..)', MarkerRegistry.fmt_first_chunk_col(r'\1'), chunk_x2)

        result = self.PADDING_HEX_CHUNK.join(chunks_x2)
        return result

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        if Settings.ignore_esc:
            return self.FALLBACK_CHAR + match.group(0)

        params_splitted = re.split(r'[^0-9]+', match.group(2))
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        mmatch = MarkerMatch(match)
        if match.group(3) == SGRSequence.TERMINATOR:
            if len(params_values) == 0:
                marker = MarkerRegistry.marker_sgr_reset
            else:
                marker = MarkerRegistry.marker_sgr
            mmatch.sgr_seq = SGRSequence(*params_values).str
        else:
            marker = MarkerRegistry.marker_esc_csi

        mmatch.marker = marker
        self._add_marker_match(mmatch)
        return marker.marker_char + match.group(0)

    def _postprocess(self, processed_input: str) -> str:
        #    processed_input = self._postprocess_input_whitespace(processed_input)
        #    processed_input = self._postprocess_input_control_chars(processed_input)
        return processed_input

    def _postprocess_input_whitespace(self, processed_input: str) -> str:
        if Settings.ignore_space:
            return processed_input

            #     for match in re.finditer(r'(\x20+)', processed_input) or []:
            #         self._add_marker_match(MarkerMatch(match, FormatRegistry.marker_space))
            #     processed_input = re.sub(r'\x20', FormatRegistry.marker_space.marker_char, processed_input)
            #
            #        for match in re.finditer(r'([\t\n\v\f\r])', processed_input) or []:
            #            marker = self._whitespace_map.get(match.group(1), None)
            #            self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
        return processed_input

    def _postprocess_input_control_chars(self, processed_input: str) -> str:
        if Settings.ignore_control:
            return processed_input
        return processed_input

    #   for match in re.finditer('r\x1b', processed_input) or []:
    #       self._add_marker_match(MarkerMatch(match, FormatRegistry.marker_escape_single, overwrite=True))
    #   for match in re.finditer(r'[\x00-\x08\x0e-\x1a\x1c-\x20\x7f]', processed_input) or []:
    #       marker = self._control_map.get(match.group(0), FormatRegistry.marker_ascii_ctrl)
    #       self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
    #   return processed_input

    def _apply_matches(self, processed_row: AnyStr, hex_row: AnyStr, local_min_pos: int, local_max_pos: int) -> Tuple[
        AnyStr, AnyStr]:
        for match_marker in self._process_matches:
            span_g0 = match_marker.match.span(0)
            if local_min_pos <= span_g0[0] <= local_max_pos or local_min_pos <= span_g0[1] <= local_max_pos:
                start_pos = max(0, span_g0[0] - local_min_pos)
                end_pos = min(local_max_pos, span_g0[1]) - local_min_pos

                processed_row = self._apply_match(processed_row, match_marker.target_text_processed,
                                                  (start_pos, end_pos))
                hex_row = self._apply_match(hex_row, match_marker.target_text_hex,
                                            self._map_pos_to_hex(start_pos, end_pos))
                match_marker.applied = True
        return processed_row, hex_row

    def _apply_match(self, row: AnyStr, target_text: Callable[[AnyStr], AnyStr], pos: Tuple[int, int]) -> AnyStr:
        (start_pos, end_pos) = pos
        left_part = row[:start_pos]
        source_text = row[start_pos:end_pos]
        right_part = row[end_pos:]
        return left_part + RESET.str + target_text(source_text) + right_part

    def _map_pos_to_hex(self, start_pos: int, end_pos: int) -> Tuple[int, int]:
        def _map(pos: int, shift: int = 0) -> int:
            chunk_num = floor(pos / self.BYTE_CHUNK_LEN)
            mapped_pos = (3 * pos) + (chunk_num * (len(self.PADDING_HEX_CHUNK) - 1))
            return max(0, mapped_pos + shift)

        return _map(start_pos), _map(end_pos - 1, 2)

    def _get_terminal_width(self) -> int:
        try:
            import shutil as _shutil
            width = _shutil.get_terminal_size().columns - 2
            return width
        except ImportError:
            return 80

    def _compute_cols_num(self, offset_len: int):
        width = self._get_terminal_width()
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
        return chunk_fit * self.BYTE_CHUNK_LEN
