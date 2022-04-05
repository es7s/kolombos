from __future__ import annotations

import re
import unicodedata
from math import floor
from typing import AnyStr, Match, Tuple, List

from pytermor import fmt, seq, autof
from pytermor.fmt import Format
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from .. import print_offset, align_offset, print_offset_debug
from ..formatter import AbstractFormatter
from ..segment.segment import Segment
from ...settings import Settings


# noinspection PyMethodMayBeStatic
class BinaryFormatter(AbstractFormatter):
    FALLBACK_CHAR = '.'

    def __init__(self):
        super().__init__()
        self.BYTE_CHUNK_LEN = 4
        self.PADDING_SECTION = 3 * ' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._buffer_raw: bytes = b''
        self._buffer_processed: str = ''

        # self._control_char_map = ConfidentDict({
        #     k: MarkerRegistry.get_control_marker(k) for k in self.CONTROL_CHARCODES
        # })
        # self._whitespace_map = {
        #     '\t': MarkerRegistry.marker_tab,
        #     '\v': MarkerRegistry.marker_vert_tab,
        #     '\f': MarkerRegistry.marker_form_feed,
        #     '\r': MarkerRegistry.marker_car_return,
        #     '\n': MarkerRegistry.marker_newline,
        # }

    def format(self, segs: List[Segment], offset: int) -> Tuple[str, str|None]:
        offset -= len(self._buffer_raw)
        self._buffer_raw += b''.join([s._raw for s in segs])
        self._buffer_processed += ''.join([autof(s.open_sgr)(s.processed) for s in segs])
        output = ''
        output_debug = ''

        if Settings.columns > 0:
            cols = Settings.columns
        else:
            cols = self._compute_cols_num(len(align_offset(offset)))

        max_buffer_len = cols
        if len(segs) == 0:  # reading finished, we have to empty the buffer completely
            max_buffer_len = 0

        # last chunk is processed twice, but that's intended; we process
        # input in pieces by <CHUNK_SIZE> bytes, not by <COLUMNS> bytes -
        # and less probably will break up some sequence
        #buffer_processed = self._process(self._buffer_raw, cols)

        local_min_pos = 0
        while len(self._buffer_raw) > max_buffer_len:
            raw_row = self._buffer_raw[:cols]
            raw_hex_row = self._format_hex_row(raw_row, cols)
            processed_row = self._buffer_processed[:cols]

            merged_row = f'{print_offset(offset, fmt.green)}' \
                         f'{raw_hex_row}{seq.RESET}{self.PADDING_SECTION}' \
                         f'{processed_row}{seq.RESET}'

            output += (merged_row + '\n')
            if Settings.debug >= 1:
                processed_hex_row = self._format_hex_row(processed_row.encode(), cols)
                print(f'{print_offset_debug("", offset, fmt.cyan)}' \
                      f'{processed_hex_row}{seq.RESET}{self.PADDING_SECTION}' \
                      f'{processed_row}{seq.RESET}')

            offset += len(raw_row)
            local_min_pos += len(raw_row)
            self._buffer_raw = self._buffer_raw[len(raw_row):]
            self._buffer_processed = self._buffer_processed[len(raw_row):]

        if len(segs) == 0:
            output += (print_offset(offset, autof(seq.HI_CYAN)) + '\n')

        return output, None

    def _format_hex_row(self, row: bytes, cols: int) -> str:
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

    def __debug_string(self, inp: AnyStr, f: Format):
        max_ln = self._get_terminal_width()
        lines = ['        │ ']*3
        for idx, char in enumerate(inp):
            if isinstance(char, int):
                schar = chr(char)
            else:
                schar = str(char)

            #if not isinstance(schar, str):
            #    schar = bytes(char)\
            #        .decode('ascii', errors='replace') \
            #        .replace('\ufffe', 'A')
            if idx % 2 == 1:
                lines = [line+str(seq.BG_BLACK) for line in lines]
            else:
                lines = [line for line in lines]

            try:
                cat = unicodedata.category(schar)
            except TypeError:
                cat = '??'

            if char == '\x1b':
                schar = autof(seq.INVERSED + seq.BOLD)(' '+MarkerRegistry.marker_sgr.marker_char)
            elif cat.startswith('C'):
                schar = fmt.bold(' Ɐ')
            elif cat.startswith('Z'):
                schar = f'{"␣":>2s}'

            lines[0] += f'{schar!s:>2s}'
            lines[1] += f'{char if isinstance(char, int) else ord(char):02x}'
            lines[2] += fmt.dim(f'{cat:>2s}')

            sep = 3*[' ']
            if idx % 2 == 1:
                sep = [str(seq.BG_COLOR_OFF)+s for s in sep]

            lines = [line+sep.pop() for line in lines]
            if len(ReplaceSGR('').invoke(lines[2])) >= max_ln - 9:
                for idx, line in enumerate(lines):
                    print(f(line))
                    lines[idx] = fmt.dim('> ')

        for line in lines:
            print(f(line))
