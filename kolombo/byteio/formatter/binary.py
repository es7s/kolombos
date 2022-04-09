from __future__ import annotations

import re
import unicodedata
from math import floor
from typing import AnyStr, Match

from pytermor import fmt, seq, autof
from pytermor.fmt import AbstractFormat, EmptyFormat, Format
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from kolombo.byteio.parser_buf import ParserBuffer
from ..chain import ChainBuffer, BufferWait
from ..formatter import AbstractFormatter
from ...console import Console, ConsoleBuffer
from ...settings import Settings


# noinspection PyMethodMayBeStatic
from ...util import get_terminal_width


class BinaryFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, data_flow: ChainBuffer):
        super().__init__(parser_buffer, data_flow)

        self.ASCII_TO_SAFE_CHAR_MAP = {
            **{b: chr(b) for b in range(0x00, 0x100)},
            **{b: '·' for b in AbstractFormatter.WHITESPACE_CHARCODES},
            **{b: '¿' for b in AbstractFormatter.CONTROL_CHARCODES},
            **{b: '¿' for b in AbstractFormatter.BINARY_CHARCODES},
        }
        self.BYTE_CHUNK_LEN = 4
        self.PADDING_SECTION = 3 * ' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._cols = Settings.columns
        self._debug_buf = Console.register_buffer(ConsoleBuffer(1, 'binform', prefix_fmt=fmt.yellow))
        self._debug_buf2 = Console.register_buffer(ConsoleBuffer(2, 'binform', prefix_fmt=fmt.yellow))

    def format(self, offset: int) -> str:
        cols = self._cols
        if cols == 0:
            prefix_example = Console.prefix_offset(offset, EmptyFormat())
            cols = self._compute_cols_num(len(prefix_example))

        final = ''
        while self._chain_buffer.data_len > 0:
            try:
                if self._parser_buffer.read_finished:
                    result = self._chain_buffer.read_all(self._format_raw)
                else:
                    result = self._chain_buffer.read(cols, self._format_raw)
            except EOFError:
                break
            except BufferWait:
                break

            bytes_read, raw_row, proc_hex_row, proc_str_row = result
            final += f'{Console.prefix_offset(offset, fmt.green)}' \
                     f'{self.PADDING_SECTION:.2s}' + \
                     f'{proc_hex_row}' + \
                     f'{self.PADDING_SECTION}' + \
                     autof(seq.CYAN)(f'│') + \
                     f'{proc_str_row}' + \
                     f'\n'
            self._debug_buf.write(f'{self._format_raw(raw_row)}'
                                  f'{self.PADDING_SECTION}' +
                                  autof(seq.CYAN)(f'│') + \
                                  f'{self._transform_to_printable(raw_row.decode("ascii", errors="replace"))}',
                                  offset=offset)

            Console.flush_buffers()
            offset += bytes_read

        if self._parser_buffer.read_finished:
            final += (Console.prefix_offset(offset, EmptyFormat()) + '\n')

        #if final_debug:
        #    final_debug += (Console.debug(self._print_debug_separator(cols, sgr=seq.CYAN), ret=True))
        #if final_debug:
        #    final += (Console.debug(self._print_debug_separator(cols, sgr=seq.CYAN), ret=True))

        return final


    def _format_raw(self, bs: bytes) -> str:
        return ''.join([f' {b:02x}' for b in bs])

    def _sanitize(self, s: str) -> str:
        return ReplaceSGR('').apply(s)

    def _transform_to_printable(self, s: str) -> str:
        result = ''
        for c in s:
            if ord(c) in AbstractFormatter.WHITESPACE_CHARCODES:
                result += '·'
            elif ord(c) not in AbstractFormatter.PRINTABLE_CHARCODES:
                result += '¿'
            else:
                result += c
        return result

    def _print_debug_separator(self, cols: int, sgr: SequenceSGR = seq.GRAY + seq.BG_BLACK) -> str:
        if Settings.debug == 0:
            return ''
        s = f'{seq.RESET}{sgr}' + '─'*6 + f'┼' + '─'*(len(self._format_hex_row(b'', cols)) + 4) + f'┼'
        l = len(ReplaceSGR().apply(s))
        return s + '─'*(max(0, get_terminal_width() - l)) + f'{seq.RESET}\n'

    def _wrap_bg(self, s: str, sgr: SequenceSGR) -> str:
        l = len(ReplaceSGR().apply(s))
        return autof(sgr)(s + ' '*(max(0, get_terminal_width() - l)))

    def _print_offset_custom(self, prefix: str, offset: int, f: Format, suffix: str = ''):
        return prefix + \
               f(
                   f'{offset:d}'.rjust(6 - len(ReplaceSGR().apply(prefix))) +
                   (f'│' if not suffix else '')
               ) + suffix + ''.rjust(2 - len(ReplaceSGR().apply(suffix))) + ('' if not suffix else '')

    def _format_hex_row(self, row: str, cols: int) -> str:
        chunks = []
        for i in range(0, cols, self.BYTE_CHUNK_LEN):
            row_part = row[(2*i):2*(i+self.BYTE_CHUNK_LEN)]
            row_part = ' '.join(re.findall('(..)', row_part))
            chunks.append(row_part)

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
            mmatch.sgr_seq = (SequenceSGR(*params_values))
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
