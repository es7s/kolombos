#!/usr/bin/env python3

from __future__ import annotations

import abc
import argparse
import os.path
import re
import sys
import traceback
from argparse import Namespace, SUPPRESS
from math import floor
from re import MULTILINE
from typing import IO, AnyStr, Optional, List, Union, Match, Dict

import pytermor
from pytermor import sanitize, build_background256_seq, build_text256_seq
from pytermor.preset import *



class Settings:
    FOCUS_SEQUENCE: bool
    FOCUS_CONTROL: bool
    FOCUS_WHITESPACE: bool
    PRINT_SEQUENCE_MARKER: bool
    PRINT_CONTROL_MARKER: bool
    PRINT_WHITESPACE_MARKER: bool
    LINE_NUMBERS: bool
    ESQ_INFO_LEVEL: int
    DISABLE_SGR_PARAM_COLORS: bool
    DISABLE_CONTEXT_COLORS: bool
    PIPE_INPUT_TO_STDERR: bool
    COLS_NUM: bool
    OVERLAY_GRID: bool

    @staticmethod
    def from_args(args: Namespace):
        Settings.FOCUS_SEQUENCE = args.focus_esq
        Settings.FOCUS_CONTROL = args.focus_control
        Settings.FOCUS_WHITESPACE = args.focus_space
        Settings.PRINT_SEQUENCE_MARKER = not args.no_esq
        Settings.PRINT_CONTROL_MARKER = not args.no_control
        Settings.PRINT_WHITESPACE_MARKER = not args.no_space

        Settings.LINE_NUMBERS = args.line_number
        Settings.ESQ_INFO_LEVEL = args.info
        Settings.DISABLE_SGR_PARAM_COLORS = args.no_color_marker
        Settings.DISABLE_CONTEXT_COLORS = args.no_color_content
        Settings.PIPE_INPUT_TO_STDERR = args.pipe_stderr

        Settings.COLS_NUM = args.columns
        Settings.OVERLAY_GRID = args.grid

        if Colombo.BINARY_MODE:
            Settings.ESQ_INFO_LEVEL = 2
            Settings.DISABLE_SGR_PARAM_COLORS = True


class Writer:
    def __init__(self):
        self._io_primary: IO = sys.stdout
        self._io_support: IO = sys.stderr

    def write_line(self, output_line: AnyStr, helper_line: Optional[AnyStr] = None):
        self._io_primary.write(output_line)

        if helper_line and Settings.PIPE_INPUT_TO_STDERR:
            self._io_support.write(helper_line)
            self._io_primary.flush()
            self._io_support.flush()


class Marker(metaclass=abc.ABCMeta):
    def __init__(self, marker_char: str):
        self._marker_char = marker_char

    @staticmethod
    def make(marker_char: str, opening_seq: Optional[SGRSequence] = None) -> str:
        return RESET.str + \
               (opening_seq.str if opening_seq else '') + \
               marker_char + \
               RESET.str

    @property
    def marker_char(self) -> str:
        return self._marker_char

    @abc.abstractmethod
    def get_fmt(self) -> Format:
        pass


class MarkerControlChar(Marker):
    def __init__(self, marker_char: str, opening_seq: SGRSequence):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq, reset=True)
        self._fmt_focused = Format(opening_seq + INVERSED + BG_BLACK, reset=True)

    def print(self, *tpl_args):
        marker = self.marker_char.format(*tpl_args)
        return self.get_fmt()(marker)

    def get_fmt(self) -> Format:
        if Settings.FOCUS_CONTROL:
            return self._fmt_focused
        return self._fmt


class MarkerWhitespace(Marker):
    _fmt = Format(DIM, DIM_BOLD_OFF)
    _fmt_focused = Format(BOLD + BG_CYAN + BLACK, reset=True)

    def __init__(self, marker_char: str, marker_char_focused_override: Optional[str] = None):
        super().__init__(marker_char)
        self._marker_char_focused = marker_char_focused_override if marker_char_focused_override else marker_char

    def print(self):
        return self.get_fmt()(self.marker_char)

    # нет времени объяснять, срочно костылим
    def get_fmt(self) -> Format:
        return self.sget_fmt()

    @staticmethod
    def sget_fmt() -> Format:
        if Settings.FOCUS_WHITESPACE:
            return MarkerWhitespace._fmt_focused
        return MarkerWhitespace._fmt

    @property
    def marker_char(self) -> str:
        if Settings.FOCUS_WHITESPACE:
            return self._marker_char_focused
        return self._marker_char


class MarkerEscapeSeq(Marker):
    def __init__(self, marker_char: str, opening_seq: SGRSequence):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq + OVERLINED, reset=True)
        self._fmt_focused = Format(opening_seq + INVERSED + BG_BLACK, reset=True)

    def print(self, additional_info: str = ''):
        return RESET.str + self.get_fmt()(self._marker_char + additional_info)

    def get_fmt(self) -> Format:
        if Settings.FOCUS_SEQUENCE:
            return self._fmt_focused
        return self._fmt


class MarkerSGRReset(Marker):
    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._fmt = Format(OVERLINED + pytermor.build_text256_seq(231), reset=True)
        self._fmt_focused = Format(INVERSED + pytermor.build_text256_seq(231), reset=True)

    def print(self):
        return RESET.str + self.get_fmt()(self._marker_char)

    def get_fmt(self) -> Format:
        if Settings.FOCUS_SEQUENCE:
            return self._fmt_focused
        return self._fmt


class MarkerSGR(Marker):
    # even though we allow to colorize content, we'll explicitly disable any inversion and overline
    #  effect to guarantee that the only inversed and/or overlined things on the screen are our markers
    # also disable blinking
    PROHIBITED_CONTENT_SEQS: SGRSequence = INVERSED_OFF + OVERLINED_OFF + BLINK_OFF

    def __init__(self, marker_char: str):
        super().__init__(marker_char)
        self._initialized: bool = False
        self._marker_seq: SGRSequence
        self._info_seq: SGRSequence

    def print(self, additional_info: str = '', seq: SGRSequence = None):
        self._init_seqs()

        result = RESET.str
        if Settings.DISABLE_SGR_PARAM_COLORS:
            result += self._marker_seq.str + self._marker_char + additional_info + seq.str
        else:
            result += self._marker_seq.str + self._marker_char + seq.str + BLINK_OFF.str + self._info_seq.str + additional_info

        if Settings.DISABLE_CONTEXT_COLORS:
            result += RESET.str  # ... content
        else:
            result += self.PROHIBITED_CONTENT_SEQS.str  # ... content
        return result

    def get_fmt(self) -> Format:
        self._init_seqs()
        return Format(self._marker_seq, reset=True)

    def _init_seqs(self):
        if self._initialized:
            return

        self._marker_seq = WHITE + BG_BLACK
        if Settings.FOCUS_SEQUENCE:
            self._info_seq = INVERSED
            if not Settings.DISABLE_SGR_PARAM_COLORS:
                self._info_seq += OVERLINED
        else:
            self._info_seq = OVERLINED
        self._marker_seq += self._info_seq
        self._initialized = True


class FormatRegistry:
    tpl_marker_ascii_ctrl = MarkerControlChar('Ɐ{}', RED)
    marker_ascii_ctrl = MarkerControlChar('Ɐ', RED)
    marker_null = MarkerControlChar('Ø', HI_RED)
    marker_bell = MarkerControlChar('Ɐ7', HI_YELLOW)
    marker_backspace = MarkerControlChar('←', HI_YELLOW)
    marker_delete = MarkerControlChar('→', HI_YELLOW)
    # 0x80-0x9f: UCC (binary mode only)

    marker_tab = MarkerWhitespace('⇥\t')  # →
    marker_space = MarkerWhitespace('␣', '·') #HI_BLUE + BG_BLACK)
    marker_newline = MarkerWhitespace('↵')
    marker_vert_tab = MarkerWhitespace('⤓')  # , MAGENTA)
    marker_form_feed = MarkerWhitespace('↡')  #, MAGENTA)
    marker_car_return = MarkerWhitespace('⇤')  #, MAGENTA)

    marker_sgr_reset = MarkerSGRReset('ϴ')
    marker_sgr = MarkerSGR('ǝ')
    marker_esc_csi = MarkerEscapeSeq('Ͻ', HI_BLUE)
    marker_esc_nf = MarkerEscapeSeq('ꟻ', HI_MAGENTA)
    marker_escape = MarkerEscapeSeq('Ǝ', HI_YELLOW)

    fmt_first_chunk_col = Format(build_text256_seq(231) + build_background256_seq(238), COLOR_OFF + BG_COLOR_OFF)
    fmt_nth_row_col = Format(build_text256_seq(231) + build_background256_seq(238) + OVERLINED, COLOR_OFF + BG_COLOR_OFF + OVERLINED_OFF)


class AbstractFormatter(metaclass=abc.ABCMeta):
    def __init__(self, _writer: Writer):
        self._writer = _writer
        self._translation_map: Dict = dict()

    def _get_translation_map(self) -> Dict:
        if not self._translation_map:
            self._build_translation_map()
        return self._translation_map

    def _build_translation_map(self):
        self._translation_map = {
            0x1b: '\0',
        }

    @abc.abstractmethod
    def format(self, raw_input: Union[AnyStr, List[AnyStr]], offset: int):
        pass

    def _process_input(self, translated_input: str) -> str:
        processed_input = re.sub(  # CSI sequences
            '\0(\\[)([0-9;:<=>?]*)([@A-Za-z\\[])',  # group 3 : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
            self._format_csi_sequence,
            translated_input
        )
        processed_input = re.sub(  # nF Escape sequences
            '\0([\x20-\x2f]+)([\x30-\x7e])',
            lambda m: self._format_generic_escape_sequence(m, FormatRegistry.marker_esc_nf),
            processed_input,
        )
        if not Colombo.BINARY_MODE:
            processed_input = re.sub(  # other escape sequences
                '\0(.)()',  # group 1 : 0x20-0x7E
                lambda m: self._format_generic_escape_sequence(m, FormatRegistry.marker_escape),
                processed_input
            )
        processed_input = self._postprocess_input_whitespace(processed_input)
        processed_input = self._postprocess_input_control_chars(processed_input)
        return processed_input

    def _postprocess_input_whitespace(self, processed_input: str) -> str:
        return processed_input

    def _postprocess_input_control_chars(self, processed_input: str) -> str:
        return processed_input

    def _filter_sgr_param(self, p):
        return len(p) > 0 and p != '0'

    @abc.abstractmethod
    def _format_csi_sequence(self, match: Match) -> AnyStr:
        pass

    @abc.abstractmethod
    def _format_generic_escape_sequence(self, match: Match, marker: MarkerEscapeSeq) -> AnyStr:
        pass


class TextFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        super().__init__(_writer)

    def _build_translation_map(self):
        super()._build_translation_map()

        if Settings.PRINT_WHITESPACE_MARKER:
            self._translation_map.update(self._get_whitespace_translation_map())
        if Settings.PRINT_CONTROL_MARKER:
            self._translation_map.update(self._get_control_translation_map())
            for i in (list(range(0x01, 0x07)) + list(range(0x0e, 0x20))):
                if i == 0x1b:
                    continue
                self._translation_map[i] = FormatRegistry.tpl_marker_ascii_ctrl.print(re.sub('0x0?', '', hex(i)))

    def _get_whitespace_translation_map(self) -> dict:
        return {
            0x09: FormatRegistry.marker_tab.print(),
            0x0b: FormatRegistry.marker_vert_tab.print(),
            0x0c: FormatRegistry.marker_form_feed.print(),
            0x0d: FormatRegistry.marker_car_return.print(),
            0x0a: FormatRegistry.marker_newline.print() + '\x0a',  # actual newline
        }

    def _get_control_translation_map(self) -> dict:
        return {
            0x00: FormatRegistry.marker_null.print(),
            0x07: FormatRegistry.marker_bell.print(),
            0x08: FormatRegistry.marker_backspace.print(),
            0x7f: FormatRegistry.marker_delete.print(),
        }

    def _postprocess_input_whitespace(self, processed_input: str) -> str:
        if Settings.PRINT_WHITESPACE_MARKER:
            processed_input = re.sub(
                '(\x20+)',
                lambda m: MarkerWhitespace.sget_fmt()(m.group(1)),
                processed_input
            )
            processed_input = re.sub('\x20', FormatRegistry.marker_space.marker_char, processed_input)
        return processed_input

    def format(self, raw_input: Union[str, List[str]], offset: int):
        from pytermor.preset import fmt_green, fmt_cyan
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = self._process_input(
                raw_input_line.translate(self._get_translation_map())
            )

            prefix = ''
            if Settings.LINE_NUMBERS:
                prefix = fmt_green('{0:2d}'.format(offset + 1)) + fmt_cyan('│')

            formatted_input = prefix + processed_input
            aligned_raw_input = (sanitize(prefix)) + raw_input_line

            self._writer.write_line(formatted_input, aligned_raw_input)
            offset += 1

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        introducer = match.group(1)  # e.g. '['
        params = match.group(2)  # e.g. '1;7'
        terminator = match.group(3)  # e.g. 'm'

        params_splitted = re.split('[^0-9]+', params)
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        if not Settings.PRINT_SEQUENCE_MARKER:
            if terminator == SGRSequence.TERMINATOR and not Settings.DISABLE_CONTEXT_COLORS:
                return SGRSequence(*params_values).str
            return ''

        info = ''
        if Settings.ESQ_INFO_LEVEL >= 1:
            info += SGRSequence.SEPARATOR.join(params_values)
        if Settings.ESQ_INFO_LEVEL >= 2:
            info = introducer + info + terminator

        if terminator == SGRSequence.TERMINATOR:
            if len(params_values) == 0:
                return FormatRegistry.marker_sgr_reset.print()
            return FormatRegistry.marker_sgr.print(info, SGRSequence(*params_values))
        else:
            return FormatRegistry.marker_esc_csi.print(info)

    def _format_generic_escape_sequence(self, match: Match, marker: MarkerEscapeSeq) -> AnyStr:
        if not Settings.PRINT_SEQUENCE_MARKER:
            return ''

        introducer = match.group(1)  # e.g. '('
        additional = match.group(2)  # e.g. 'B'
        if introducer == ' ':
            introducer = FormatRegistry.marker_space.marker_char
        info = ''
        if Settings.ESQ_INFO_LEVEL >= 1:
            info += introducer
        if Settings.ESQ_INFO_LEVEL >= 2:
            info += additional

        return marker.print(info)


class MarkerMatch:
    def __init__(self, match: Match, marker: Marker = None, overwrite: bool = False):
        self.match = match
        self.marker = marker
        self.overwrite = overwrite
        self.sgr_seq = None


class BinaryFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        super().__init__(_writer)

        self.BYTE_CHUNK_LEN = 4
        self.PLACEHOLDER_CHAR = '.'

        self.PADDING_SECTION = 3*' '
        self.PADDING_HEX_CHUNK = 2 * ' '

        self._buffer_raw: bytes = bytes()
        self._buffer_processed: str = ''
        self._process_matches: List[MarkerMatch] = []

        self._row_num = 0

        hexlist = ''
        placeholder_code = ord(self.PLACEHOLDER_CHAR)
        for i in range(0, 0x100):
            if i >= 0x7f:
                hexlist += '{:02x}'.format(placeholder_code)
            else:
                hexlist += '{:02x}'.format(i)
        self._byte_table = bytes.fromhex(hexlist)

        self._whitespace_map = {
            '\t': MarkerWhitespace(FormatRegistry.marker_tab.marker_char[0]),
            '\v': FormatRegistry.marker_vert_tab,
            '\f': FormatRegistry.marker_form_feed,
            '\r': FormatRegistry.marker_car_return,
            '\n': FormatRegistry.marker_newline,
        }
        self._control_map = {
            '\x00': FormatRegistry.marker_null,
            '\x08': FormatRegistry.marker_backspace,
            '\x7f': FormatRegistry.marker_delete,
        }

    def _build_translation_map(self):
        self._translation_map = {
            0x1b: '\0',
        }

        if not Settings.PRINT_CONTROL_MARKER:
            self._translation_map.update({
                b: self.PLACEHOLDER_CHAR for b in (
                    list(range(0x00, 0x08)) +
                    list(range(0x0e, 0x1b)) +
                    list(range(0x1c, 0x20)) +
                    [0x7f]
                )})

        if not Settings.PRINT_WHITESPACE_MARKER:
            self._translation_map.update({b: self.PLACEHOLDER_CHAR for b in list(range(0x09, 0x0e))})

    def _postprocess_input_whitespace(self, processed_input: str) -> str:
        if not Settings.PRINT_WHITESPACE_MARKER:
            return processed_input

        for match in re.finditer('(\x20+)', processed_input) or []:
            self._process_matches.append(MarkerMatch(match, FormatRegistry.marker_space))
        processed_input = re.sub('\x20', FormatRegistry.marker_space.marker_char, processed_input)

        for match in re.finditer('([\t\n\v\f\r])', processed_input) or []:
            marker = self._whitespace_map.get(match.group(1), None)
            self._process_matches.append(MarkerMatch(match, marker, overwrite=True))
        return processed_input

    def _postprocess_input_control_chars(self, processed_input: str) -> str:
        if not Settings.PRINT_CONTROL_MARKER:
            return processed_input

        for match in re.finditer('([\0\a\b\x0e-\x1a\x1c-\x20\x7f])', processed_input) or []:
            marker = self._control_map.get(match.group(1), FormatRegistry.marker_ascii_ctrl)
            self._process_matches.append(MarkerMatch(match, marker, overwrite=True))
        return processed_input

    #

    def format(self, raw_input: bytes, offset: int):
        offset -= len(self._buffer_raw)
        self._buffer_raw += raw_input

        if Settings.COLS_NUM > 0:
            cols = Settings.COLS_NUM
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
            is_guide_row = (Settings.OVERLAY_GRID and (self._row_num % (2 * self.BYTE_CHUNK_LEN)) == 0)
            raw_row = self._buffer_raw[:cols]
            local_max_pos = local_min_pos + len(raw_row)

            processed_row = self._apply_matches(buffer_processed[:cols], local_min_pos, local_max_pos) + RESET.str
            hex_row = self._format_hex_row(raw_row, cols, is_guide_row)
            hex_row = self._apply_matches(hex_row, local_min_pos, local_max_pos, True) + RESET.str

            # @TODO: control char focus
            # @TODO whitespace focus

            merged_row = '{}{}{}'.format(self._print_offset(offset), hex_row, processed_row)
            if is_guide_row:
                merged_row = FormatRegistry.fmt_nth_row_col(processed_row)

            self._writer.write_line(merged_row + '\n')

            offset += len(raw_row)
            local_min_pos += len(raw_row)
            self._buffer_raw = self._buffer_raw[len(raw_row):]
            buffer_processed = buffer_processed[len(raw_row):]  # should be equal
            self._row_num += 1

        if len(raw_input) == 0:
            self._writer.write_line(self._print_offset(offset, True) + '\n')

    def _format_offset(self, offset: int) -> AnyStr:
        return '{:08x}{}'.format(offset, self.PADDING_SECTION)

    def _print_offset(self, offset: int, is_total: bool = False):
        fmt = fmt_green
        if is_total:
            fmt = Format(HI_BLUE)
        return re.sub('^(0+)(\S+)(\s)', fmt(DIM.str + '\\1' + DIM_BOLD_OFF.str + '\\2') + fmt_cyan('│'), self._format_offset(offset))

    def _format_hex_row(self, row: bytes, cols: int, is_guide_row: bool = False) -> AnyStr:
        chunks = []
        for i in range(0, cols, self.BYTE_CHUNK_LEN):
            row_part = row[i:i+self.BYTE_CHUNK_LEN]
            hexs = row_part.hex()
            if len(row_part) < self.BYTE_CHUNK_LEN:
                hexs += '  ' * (self.BYTE_CHUNK_LEN - len(row_part))
            hexs = ' '.join(re.findall('(..)', hexs))
            chunks.append(hexs)

        chunks_len = len(chunks)
        chunks_x2 = [chunks[i] + self.PADDING_HEX_CHUNK + chunks[i + 1] for i in range(0, chunks_len - 1, 2)]
        if chunks_len % 2 == 1:
            chunks_x2.append(chunks[chunks_len-1])

        if Settings.OVERLAY_GRID and not is_guide_row:
            for i, chunk_x2 in enumerate(chunks_x2):
                chunks_x2[i] = re.sub('^(..)', FormatRegistry.fmt_first_chunk_col('\\1'), chunk_x2)

        result = self.PADDING_HEX_CHUNK.join(chunks_x2) + RESET.str + self.PADDING_SECTION
        return result

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        params_splitted = re.split('[^0-9]+', match.group(2))
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        marker = None
        mmatch = MarkerMatch(match)

        if Settings.PRINT_SEQUENCE_MARKER:
            if match.group(3) == SGRSequence.TERMINATOR:
                if len(params_values) == 0:
                    marker = FormatRegistry.marker_sgr_reset
                else:
                    marker = FormatRegistry.marker_sgr
                mmatch.sgr_seq = SGRSequence(*params_values).str
            else:
                marker = FormatRegistry.marker_esc_csi

        if marker:
            marker_char = marker.marker_char
            mmatch.marker = marker
            self._process_matches.append(mmatch)
        else:
            marker_char = self.PLACEHOLDER_CHAR
        return marker_char + match.group(1) + match.group(2) + match.group(3)

    def _format_generic_escape_sequence(self, match: Match, marker: MarkerEscapeSeq) -> AnyStr:
        marker_char = self.PLACEHOLDER_CHAR

        if Settings.PRINT_SEQUENCE_MARKER:
            marker = FormatRegistry.marker_escape
            marker_char = FormatRegistry.marker_escape.marker_char
            self._process_matches.append(MarkerMatch(match, marker))

        return marker_char + match.group(1) + match.group(2)

    def _decode_and_process(self, raw_input: bytes, cols: int) -> AnyStr:
        decoded = raw_input.translate(self._byte_table).decode()
        #if Settings.OVERLAY_GRID and not is_guide_row:
        #    formatted = re.sub('(.)(.{,7})', FormatRegistry.fmt_first_chunk_col('\\1') + '\\2', formatted)
        translated = decoded.translate(self._get_translation_map())
        processed = self._process_input(translated)
        sanitized = sanitize(processed)
        if len(sanitized) != len(decoded):
            raise RuntimeError('Fatal: length mismatch. Dumps:', {
                'raw_input': raw_input,
                'translated': translated,
                'processed': processed,
                'sanitized': sanitized,
            })
        return processed + ' ' * (cols - len(processed))

    def _apply_matches(self, row: str, local_min_pos: int, local_max_pos: int, is_hex_row: bool = False) -> str:
        for mm in self._process_matches:
            span_g0 = mm.match.span(0)
            if local_min_pos <= span_g0[0] <= local_max_pos or local_min_pos <= span_g0[1] <= local_max_pos:
                start_pos = max(0, span_g0[0] - local_min_pos)
                end_pos = min(local_max_pos, span_g0[1]) - local_min_pos

                if is_hex_row:
                    start_pos = self._map_pos_to_hex_row(start_pos)
                    end_pos = self._map_pos_to_hex_row(end_pos, end=True)

                left_part = row[:start_pos]
                mid_part = row[start_pos:end_pos]
                right_part = row[end_pos:]

                fmt = mm.marker.get_fmt()
                if is_hex_row:
                    mid_part = ' '.join([fmt(b) for b in mid_part.split(' ')])
                else:
                    if mm.overwrite:
                        mid_part = fmt(mm.marker.marker_char)
                    else:
                        mid_part = fmt(mid_part)

                if mm.sgr_seq and not Settings.DISABLE_CONTEXT_COLORS:
                    right_part = mm.sgr_seq + MarkerSGR.PROHIBITED_CONTENT_SEQS.str + right_part

                row = left_part + RESET.str + mid_part + right_part

        return row

    def _map_pos_to_hex_row(self, pos: int, end: bool = False) -> int:
        if end:
            pos -= 1
        chunk_num = floor(pos / self.BYTE_CHUNK_LEN)
        mapped_pos = (3 * pos) + (chunk_num * (len(self.PADDING_HEX_CHUNK) - 1))
        if end:
            mapped_pos += 2
        return mapped_pos

    def _get_terminal_width(self):
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


class AbstractReader(metaclass=abc.ABCMeta):
    _filename: Optional[str]
    _io: Optional
    _formatter: AbstractFormatter
    _offset: int = 0

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        self._filename = filename
        self._formatter = formatter

    def read(self):
        self._open()
        try:
            self._read_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self._close()

    @abc.abstractmethod
    def _open(self) -> None:
        pass

    @abc.abstractmethod
    def _read_loop(self) -> None:
        pass

    @property
    def _is_arg_stdin(self) -> bool:
        return not self._filename or self._filename == '-'

    def _close(self):
        if self._io and not self._io.closed:
            self._io.close()


class TextReader(AbstractReader):
    _READ_LINES_COUNT: int = 10

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        super().__init__(filename, formatter)

    def _open(self) -> None:
        if self._is_arg_stdin:
            self._io = sys.stdin
        else:
            self._io = open(self._filename, 'rt')

    def _read_loop(self) -> None:
        while raw_input := self._io.readlines(TextReader._READ_LINES_COUNT):
            self._formatter.format(raw_input, self._offset)
            self._offset += len(raw_input)


class BinaryReader(AbstractReader):
    _READ_CHUNK_SIZE: int = 1024

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        super().__init__(filename, formatter)

    def _open(self) -> None:
        if self._is_arg_stdin:
            self._io = sys.stdin.buffer
        else:
            self._io = open(self._filename, 'rb')

    def _read_loop(self) -> None:
        while raw_input := self._io.read(BinaryReader._READ_CHUNK_SIZE):
            self._formatter.format(raw_input, self._offset)
            self._offset += len(raw_input)
        self._formatter.format(bytes(), self._offset)


class Colombo:
    BINARY_MODE: bool

    def run(self):
        _hanlder = ExceptionHandler()
        try:
            self._invoke()
        except Exception as e:
            _hanlder.handle(e)
        print()

    def _invoke(self):
        parser = argparse.ArgumentParser(
            description='escape sequences and control characters visualiser',
            epilog='example: colombo -e -i 2 --no-space file.txt',
            add_help=False,
            formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
        )
        modes_group = parser.add_argument_group('mode selection')
        modes_group.add_argument('-t', '--text', action='store_true', default=True, help='open file in text mode (this is the default)')
        modes_group.add_argument('-b', '--binary', action='store_true', default=False, help='open file in binary mode')
        modes_group.add_argument('-l', '--legend', action='store_true', help='show annotation symbol list and exit')
        modes_group.add_argument('-h', '--help', action='help', default=SUPPRESS, help='show this help message and exit')

        generic_group = parser.add_argument_group('generic options')
        generic_group.add_argument('filename', metavar='<file>', nargs='?', help='file to read from; if empty or "-", read stdin instead')
        generic_group.add_argument('-e', '--focus-esq', action='store_true', default=False, help='highlight escape sequences markers')
        generic_group.add_argument('-s', '--focus-space', action='store_true', default=False, help='highlight whitespace markers')
        generic_group.add_argument('-c', '--focus-control', action='store_true', default=False, help='highlight control char markers')
        generic_group.add_argument('-E', '--no-esq', action='store_true', default=False, help='do not print escape sequence markers')
        generic_group.add_argument('-S', '--no-space', action='store_true', default=False, help='do not print whitespace markers')
        generic_group.add_argument('-C', '--no-control', action='store_true', default=False, help='do not print control char markers')

        text_mode_group = parser.add_argument_group('text mode only')
        text_mode_group.add_argument('-i', '--info', metavar='<level>', action='store', type=int, default=1, help='escape sequence marker verbosity (0-2, default 1)')
        text_mode_group.add_argument('-L', '--line-number', action='store_true', default=False, help='print line numbers')
        text_mode_group.add_argument('--no-color-marker', action='store_true', default=False, help='disable applying file content formatting to SGR markers')
        text_mode_group.add_argument('--no-color-content', action='store_true', default=False, help='disable applying file content formatting to the output')
        text_mode_group.add_argument('--pipe-stderr', action='store_true', default=False, help='send raw input lines to stderr along with default output')

        bin_mode_group = parser.add_argument_group('binary mode only')
        bin_mode_group.add_argument('-n', '--columns', metavar='<num>', action='store', type=int, default=0, help='output <num> bytes per line (default is 0 = auto)')
        bin_mode_group.add_argument('-g', '--grid', action='store_true', default=False, help='display on the table 8x8 overlay grid')
        args = parser.parse_args()

        if args.legend:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'colombo-legend.ansi'), 'rt') as f:
                print(f.read())
                exit(0)

        Colombo.BINARY_MODE = args.binary
        Settings.from_args(args)

        writer = Writer()
        if self.BINARY_MODE:
            reader = BinaryReader(args.filename, BinaryFormatter(writer))
        else:
            reader = TextReader(args.filename, TextFormatter(writer))

        try:
            reader.read()
        except UnicodeDecodeError:
            if not self.BINARY_MODE:
                print('Binary data detected, cannot proceed in text mode')
                print('Use -b option to run in binary mode')
            else:
                raise


class ExceptionHandler:
    def __init__(self):
        self.format: Format = fmt_red

    def handle(self, e: Exception):
        self._log_traceback(e)
        print()
        exit(1)

    def _write(self, s: str):
        print(self.format(s), file=sys.stderr)

    def _log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n')
                    for line
                    in traceback.format_exception(e.__class__, e, ex_traceback)]
        self._write("\n".join(tb_lines))


if __name__ == '__main__':
    Colombo().run()
