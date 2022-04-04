import re
import unicodedata
from math import floor
from typing import List, AnyStr, Union, Match, Tuple, Callable, Pattern
from unicodedata import digit

from pytermor import fmt, seq, autof
from pytermor.fmt import Format
from pytermor.seq import SequenceSGR
from pytermor.util import apply_filters, ReplaceSGR, StringFilter

from ..formatter import AbstractFormatter
from ..marker.registry import MarkerRegistry
from ..marker.utf8 import MarkerUTF8
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

        self._filter_utf8_seq_and_unicode_control = StringFilter[bytes](
            lambda s: re.sub(b'[\xc2-\xdf][\x80-\xbf]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xe1-\xec\xee\xef][\x80-\xbf]{2}|\xed[\x80-\x9f][\x80-\xbf]|\xf0[\x90-\xbf][\x80-\xbf]{2}|[\xf1-\xf3][\x80-\xbf]{3}|\xf4[\x80-\x8f][\x80-\xbf]{2}|([\x80-\xff])',
                             self._format_utf8_seq_and_unicode_control, s)
        )
        self._filters_pre.append(self._filter_utf8_seq_and_unicode_control)

        self._control_char_map = ConfidentDict({
            k: MarkerRegistry.get_control_marker(k) for k in self.CONTROL_CHARCODES
        })
        self._whitespace_map = {
            '\t': MarkerRegistry.marker_tab,
            '\v': MarkerRegistry.marker_vert_tab,
            '\f': MarkerRegistry.marker_form_feed,
            '\r': MarkerRegistry.marker_car_return,
            '\n': MarkerRegistry.marker_newline,
        }

    def get_fallback_char(self) -> AnyStr:
        return self.FALLBACK_CHAR

    def _get_filter_control(self) -> Pattern:
        return re.compile(r'([\x00-\x08\x0e-\x1f\x7f])')

    def format(self, raw_input: Union[AnyStr], offset: int):
        offset -= len(self._buffer_raw)
        self._buffer_raw += raw_input

        if Settings.columns > 0:
            cols = Settings.columns
        else:
            cols = self._compute_cols_num(len(self._format_offset(offset)))

        max_buffer_len = cols
        if len(raw_input) == 0:  # reading finished, we have to empty the buffer completely
            max_buffer_len = 0

        self._process_matches.clear()
        buffer_processed = self._decode_and_process(self._buffer_raw, cols)

        # iterate backwards, so updates to the processed_row doesn't mess up next offsets:
        # : self._process_matches.reverse()
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

            #self.__debug_string(raw_row, fmt.green, 'raw')
            #self.__debug_string(buffer_processed[:cols], fmt.cyan, 'processed')
            #self.__debug_string(processed_row, fmt.blue, 'with_mms')

            # key difference beetween process() and postprocess():
            #  process() keeps string size constant (so BYTE <N> in raw input
            #    in binary mode always corresponds to CHAR <N> in processed input)
            #  postprocess() doesn't care
            postprocessed_row = self._postprocess_input(processed_row)

            merged_row = f'{self._print_offset(offset)}' \
                         f'{hex_row}{seq.RESET}{self.PADDING_SECTION}' \
                         f'{postprocessed_row}{seq.RESET}'
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
        f = fmt.green
        if is_total:
            f = Format(seq.HI_CYAN)
        return re.sub(r'^(0+)(\S+)(\s)',
                      f(fmt.dim(r'\1') + r'\2') + fmt.cyan('│'),
                      self._format_offset(offset))

    def _add_marker_match(self, fsegment: MarkerMatch):  # @todo formatted segment
        self._process_matches.append(fsegment)

    def _decode_and_process(self, raw_input: bytes, cols: int) -> AnyStr:
        decoded = self._preprocess_input(raw_input)\
            .decode('ascii', errors='replace')\
            .replace('\ufffd', '\xfe')

        # if Settings.OVERLAY_GRID and not is_guide_row:
        #    formatted = re.sub('(.)(.{,7})', FormatRegistry.fmt_first_chunk_col('\\1') + '\\2', formatted)

        processed = self._process_input(decoded)
        sanitized = apply_filters(processed, ReplaceSGR(''))
        assert len(sanitized) == len(decoded)
        return f'{processed}{seq.RESET}{" " * (cols - len(processed))}'

    def _format_hex_row(self, row: bytes, cols: int, is_guide_row: bool = False) -> str:
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

    def _format_csi_sequence(self, match: Match) -> str:
        if Settings.ignore_esc:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
            return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))

        params_splitted = re.split(r'[^0-9]+', match.group(2))
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        mmatch = MarkerMatch(match)
        if match.group(3) == SequenceSGR.TERMINATOR:
            if len(params_values) == 0:
                marker = MarkerRegistry.marker_sgr_reset
            else:
                marker = MarkerRegistry.marker_sgr
            mmatch.sgr_seq = str(SequenceSGR(*params_values))
        else:
            marker = MarkerRegistry.marker_esq_csi

        mmatch.set_marker(marker)
        self._add_marker_match(mmatch)
        return marker.marker_char + ''.join(match.groups())

    def _format_generic_escape_sequence(self, match: Match) -> str:
        if Settings.ignore_esc:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
            return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))

        introducer = match.group(1)
        if introducer == ' ':
            introducer = MarkerRegistry.marker_space.marker_char
        charcode = ord(introducer)
        marker = MarkerRegistry.get_esq_marker(charcode)
        self._add_marker_match(MarkerMatch(match, marker))
        return marker.marker_char + ''.join(match.groups())

    def _format_control_char(self, match: Match) -> AnyStr:
        if Settings.ignore_control:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True))
            return MarkerRegistry.marker_ignored.marker_char

        charcode = ord(match.group(1))
        marker = self._control_char_map.require_or_die(charcode)
        self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
        return match.group(1)

    def _format_utf8_seq_and_unicode_control(self, match: Match) -> AnyStr:
        if match.group(1):
            if Settings.ignore_control:
                self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True))
                return match.group(1)
            return self._format_control_char(match)

        if Settings.ignore_utf8:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored, overwrite=True, autosize=True))
            return match.group(0)
        elif Settings.decode:
            self._add_marker_match(MarkerMatch(match, MarkerUTF8(match.group(0).decode()), overwrite=True))
            return match.group(0)
        self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_utf8, overwrite=True, autosize=True))
        return match.group(0)

    def _format_space(self, match: Match) -> str:
        if Settings.ignore_space:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
            return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))

        self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_space))
        return MarkerRegistry.marker_space.marker_char * len(match.group(0))

    def _format_whitespace(self, match: Match) -> str:
        if Settings.ignore_space:
            self._add_marker_match(MarkerMatch(match, MarkerRegistry.marker_ignored))
            return MarkerRegistry.marker_ignored.marker_char * len(match.group(0))

        marker = self._whitespace_map.get(match.group(1))
        self._add_marker_match(MarkerMatch(match, marker, overwrite=True))
        return marker.marker_char

    def _apply_matches(self, processed_row: AnyStr, hex_row: AnyStr, local_min_pos: int, local_max_pos: int) -> Tuple[
        AnyStr, AnyStr]:
        for match_marker in self._process_matches:
            span_g0 = match_marker.match.span(0)
            if local_min_pos <= span_g0[0] < local_max_pos or local_min_pos < span_g0[1] < local_max_pos:
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
        return f'{left_part}{target_text(source_text)}{right_part}'

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

    def __debug_string(self, s: AnyStr, f: Format, desc: str = None):
        if isinstance(s, bytes):
            s = s.decode(errors='replace')

        print(f(fmt.bold((desc or 'debug').upper()) + f' [len {len(s)}]'))

        max_ln = self._get_terminal_width()
        lines = [' ']*3
        lines[0] = '\n'+lines[0]
        even = True
        for i, c in enumerate(s):
            even = not even
            if even:
                lines = [line+str(seq.BG_BLACK) for line in lines]
            else:
                lines = [line for line in lines]

            cat = unicodedata.category(c)
            byts = c.encode()
            if c == '\x1b':
                c = autof(seq.INVERSED + seq.BOLD)(' '+MarkerRegistry.marker_sgr.marker_char)
            elif cat.startswith('C'):
                c = fmt.inversed(' Ɐ')
            elif cat.startswith('Z'):
                c = f'{"␣":>2s}'

            if len(byts) > 1:
                lines[0] += fmt.dim(''.join([f'{" ·":>2s}' for _ in byts[1:]]) + ' ' ) + c
            else:
                lines[0] += f'{c:>2s}'

            lines[1] += (''.join([f'{b:x}' for b in byts]))
            lines[2] += fmt.dim(f'{cat:>{2*len(byts)}s}')

            sep = 3*[' ']
            if i % 10 == 9:
                sep = 3*[fmt.dim(' │ ')]
            if even:
                sep = [str(seq.BG_COLOR_OFF)+s for s in sep]

            lines = [line+sep.pop() for line in lines]

            ln = len(ReplaceSGR('').invoke(lines[2]))
            if ln >= max_ln - 9:
                for idx, line in enumerate(lines):
                    print(f(line))
                    lines[idx] = ('\n' if idx == 0 else '') + fmt.dim('> ')
                ln = 0

        for line in lines:
            print(f(line))
        print()
