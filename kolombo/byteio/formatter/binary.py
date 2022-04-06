from __future__ import annotations

import re
import unicodedata
from math import floor
from typing import AnyStr, Match, Tuple, List

from pytermor import fmt, seq, autof
from pytermor.fmt import Format, EmptyFormat
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from .. import print_offset, align_offset
from ..formatter import AbstractFormatter
from ..segment.segment import Segment
from kolombo.byteio.sequencer import Sequencer
from ...console import Console
from ...settings import Settings


# noinspection PyMethodMayBeStatic
class BinaryFormatter(AbstractFormatter):
    def __init__(self, sequencer: Sequencer):
        super().__init__(sequencer)

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
        # }'

    def format(self):
        offset = self._sequencer.offset_raw

        cols = Settings.columns
        if cols == 0:
            cols = self._compute_cols_num(len(align_offset(offset)))

        final = ''
        final_debug = ''
        while seg := self._sequencer.pop_segment():
            if final_debug:
                final_debug += Console.debug_on(self._print_debug_separator(cols, sgr=seq.GRAY), 3, ret=True)
            final_debug += Console.debug_on(self._wrap_bg(
                f'POP {id(seg):x} {seg!r}',
                seq.BG_BLACK) + '\n', 3, ret=True)
            if not seg:
                continue
            seg_offset = self._sequencer.offset_raw
            self._buffer_raw += seg.raw
            self._buffer_processed += f'{self._sequencer.close_segment()(seg.processed)}'

            seg_row = seg.raw[:cols]
            final_debug += Console.debug_on(
                self._wrap_bg('{}{}{}{}'.format(
                    self._print_offset_custom('', seg_offset, autof(seq.HI_MAGENTA),
                                              suffix=autof(seq.GRAY)('│')+autof(seq.INVERSED if seg.type_label.isupper() else seq.DIM
                                                                                     )(f'{seg.type_label}')+' '),
                    self._format_hex_row(seg_row, cols),
                    autof(seq.GRAY)('  │'),
                    self._translate_ascii_only(seg_row.decode())
                ), seq.BG_BLACK) + '\n', 2, ret=True
            )
            seg_offset += len(seg.raw)

            max_buffer_len = cols
            if self._sequencer.read_finished:  # reading finished, we have to empty the buffer completely
                max_buffer_len = 0

            while len(self._buffer_raw) > max_buffer_len:
                raw_row = self._buffer_raw[:cols]
                raw_hex_row = self._format_hex_row(raw_row, cols)
                processed_row = self._buffer_processed[:cols]

                final += f'{print_offset(offset, fmt.green)}' \
                         f'{raw_hex_row}  ' + \
                         autof(seq.CYAN)(f'│') + \
                         f'{processed_row}' + \
                         f'\n'

                final_debug += Console.debug(
                    self._wrap_bg('{}{}{}{}'.format(
                        self._print_offset_custom("", offset, autof(seq.HI_BLUE), suffix=autof(seq.GRAY)("│  ")),
                        self._format_hex_row(self._sanitize(processed_row), cols),
                        autof(seq.GRAY)('  │'),
                        self._translate_ascii_only(processed_row)),
                        seq.BG_BLACK) + '\n',
                    ret=True)

                offset += len(raw_row)
                self._buffer_raw = self._buffer_raw[len(raw_row):]
                self._buffer_processed = self._buffer_processed[len(raw_row):]

        if self._sequencer.read_finished:
            final += (print_offset(offset, autof(seq.HI_CYAN)) + '\n')

        if final_debug:
            self._sequencer.append_final(Console.debug(self._print_debug_separator(cols, sgr=seq.CYAN), ret=True))
        self._sequencer.append_final(final_debug)
        if final:
            self._sequencer.append_final(Console.debug(self._print_debug_separator(cols, sgr=seq.CYAN), ret=True))
        self._sequencer.append_final(final)

    def _sanitize(self, s: str) -> bytes:
        return s.encode('ascii', errors='replace')

    def _translate_ascii_only(self, s: str) -> str:
        return "".join([
            chr(b) if b in AbstractFormatter.PRINTABLE_CHARCODES else "." for b in self._sanitize(s)
        ])

    def _print_debug_separator(self, cols: int, sgr: SequenceSGR = seq.GRAY + seq.BG_BLACK) -> str:
        if Settings.debug == 0:
            return ''
        s = f'{seq.RESET}{sgr}' + '─'*6 + f'┼' + '─'*(len(self._format_hex_row(b'', cols)) + 4) + f'┼'
        l = len(ReplaceSGR()(s))
        return s + '─'*(max(0, self._get_terminal_width() - l)) + f'{seq.RESET}\n'

    def _wrap_bg(self, s: str, sgr: SequenceSGR) -> str:
        l = len(ReplaceSGR()(s))
        return autof(sgr)(s + ' '*(max(0, self._get_terminal_width() - l)))

    def _print_offset_custom(self, prefix: str, offset: int, f: Format, suffix: str = ''):
        return prefix + \
               f(
                   f'{offset:d}'.rjust(6 - len(ReplaceSGR().invoke(prefix))) +
                   (f'│' if not suffix else '')
               ) + suffix + ''.rjust(2 - len(ReplaceSGR().invoke(suffix))) + ('' if not suffix else '')

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
