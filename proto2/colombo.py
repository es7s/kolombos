#!/usr/bin/env python3

from __future__ import annotations

import abc
import os.path
import re
import sys
import traceback
from argparse import Namespace, SUPPRESS, Action, ArgumentParser, HelpFormatter
from functools import reduce
from math import floor
from typing import IO, AnyStr, Optional, List, Union, Match, Dict, Iterable, TypeVar, Callable, Type, \
    Tuple

import pytermor
from pytermor import build_background256_seq, build_text256_seq
from pytermor.preset import *


class StringFilter:
    def __init__(self, fn: Callable):
        self._fn = fn

    def __call__(self, s: str):
        return self._fn(s)


class ReplaceSGRSequences(StringFilter):
    def __init__(self, repl: AnyStr):
        super().__init__(lambda s: re.sub(r'\033\[([0-9;:<=>?]*)([@A-Za-z])', repl, s))


class ReplaceNonAsciiCharacters(StringFilter):
    def __init__(self, repl: AnyStr):
        super().__init__(lambda s: re.sub(r'[^\x00-\x7f]', repl, s))


def apply_filters(string: AnyStr, *args: StringFilter | Type[StringFilter]) -> AnyStr:
    filters = map(lambda t: t() if isinstance(t, type) else t, args)
    return reduce(lambda s, f: f(s), filters, string)


class Settings(Namespace):
    binary: bool
    filename: Optional[str]
    focus_control: bool
    focus_esc: bool
    focus_space: bool
    grid: bool
    ignore_control: bool
    ignore_esc: bool
    ignore_space: bool
    info: int
    legend: bool
    no_line_numbers: bool
    lines: int
    bytes: int
    no_color_content: bool
    no_color_marker: bool
    pipe_stderr: bool
    text: bool
    columns: int

    @staticmethod
    def effective_info_level() -> int:
        if Settings.binary:
            return 2
        return Settings.info


class Writer:
    def __init__(self):
        self._io_primary: IO = sys.stdout
        self._io_support: IO = sys.stderr

    def write_line(self, output_line: AnyStr, helper_line: Optional[AnyStr] = None):
        self._io_primary.write(output_line)

        if helper_line and Settings.pipe_stderr:
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
        if Settings.focus_control:
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
        if Settings.focus_space:
            return MarkerWhitespace._fmt_focused
        return MarkerWhitespace._fmt

    @property
    def marker_char(self) -> str:
        if Settings.focus_space:
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
        if Settings.focus_esc:
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
        if Settings.focus_esc:
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
        result = RESET.str + self._marker_seq.str + self._marker_char

        if Settings.no_color_markers:
            result += additional_info + seq.str
        else:
            result += seq.str + self.PROHIBITED_CONTENT_SEQS.str + self._info_seq.str + additional_info

        if Settings.no_color_content:
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
        if Settings.focus_esc:
            self._info_seq = INVERSED
            if not Settings.no_color_markers:
                self._info_seq += OVERLINED
        else:
            self._info_seq = OVERLINED
        self._marker_seq += self._info_seq
        self._initialized = True


class FormatRegistry:
    _tpl_marker_ascii_ctrl = MarkerControlChar('Ɐ{}', RED)

    @staticmethod
    def get_control_marker(charcode: int, text_max_len: int = 0):
        if charcode == 0x00:
            return MarkerControlChar('Ø', HI_RED)
        elif charcode == 0x1b:  # standalone escape
            return MarkerControlChar('Ǝ', HI_YELLOW)
        elif charcode == 0x08:
            return MarkerControlChar('←', RED)
        elif charcode == 0x7f:
            return MarkerControlChar('→', RED)
        elif 0x00 <= charcode < 0x20:
            return MarkerControlChar('Ɐ{:x}'.format(charcode)[:text_max_len], RED)
        elif 0x80 <= charcode <= 0xff:
            return MarkerControlChar('U{:x}'.format(charcode)[:text_max_len], MAGENTA)
        raise ValueError('Unknown control character code: "{}'.format(charcode))

    @staticmethod
    def get_esq_marker(introducer_charcode: int):
        if 0x20 <= introducer_charcode < 0x30:
            return MarkerEscapeSeq('ꟻ', GREEN)
        elif 0x30 <= introducer_charcode:
            return MarkerEscapeSeq('Ǝ', YELLOW)
        raise ValueError('Unknown escape sequence introducer code: "{}'.format(introducer_charcode))

    marker_tab = MarkerWhitespace('⇥\t')
    marker_space = MarkerWhitespace('␣', '·')
    marker_newline = MarkerWhitespace('↵')
    marker_vert_tab = MarkerWhitespace('⤓')
    marker_form_feed = MarkerWhitespace('↡')
    marker_car_return = MarkerWhitespace('⇤')

    marker_sgr_reset = MarkerSGRReset('ϴ')
    marker_sgr = MarkerSGR('ǝ')
    marker_esc_csi = MarkerEscapeSeq('Ͻ', GREEN)

    fmt_first_chunk_col = Format(build_text256_seq(231) + build_background256_seq(238), COLOR_OFF + BG_COLOR_OFF)
    fmt_nth_row_col = Format(build_text256_seq(231) + build_background256_seq(238) + OVERLINED,
                             COLOR_OFF + BG_COLOR_OFF + OVERLINED_OFF)


KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.


class ConfidentDict(Dict[KT, VT]):
    def find_or_die(self, key: KT) -> VT | None:
        if key not in self:
            raise LookupError('Key not found: "{}"', key)
        return self[key]

    def require_or_die(self, key: KT) -> VT:
        val = self.find_or_die(key)
        if val is None:
            raise ValueError('Value is None: "{}"'.format(key))
        return val


class AbstractFormatter(metaclass=abc.ABCMeta):
    CONTROL_CHARCODES = list(range(0x00, 0x09)) + list(range(0x0e, 0x20)) + list(range(0x7f, 0x100))
    WHITESPACE_CHARCODES = list(range(0x09, 0x0e)) + [0x20]

    def __init__(self, _writer: Writer):
        self._writer = _writer

        self._filter_sgr = StringFilter(  # CSI (incl. SGR) sequences
            lambda s: re.sub(r'\x1b(\[)([0-9;:<=>?]*)([@A-Za-z\[])', self._format_csi_sequence, s)
        )                      # @TODO group 3  ^^^^^^^^^^^^^^^^^^  : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
        self._filter_nf = StringFilter(   # nF Escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x2f])([\x20-\x2f]*)([\x30-\x7e])', self._format_generic_escape_sequence, s)
        )
        self._filter_esq = StringFilter(  # other escape sequences
            lambda s: re.sub(r'\x1b([\x20-\x7f])()()', self._format_generic_escape_sequence, s)
        )
        self._filter_control = StringFilter(  # control chars incl. standalone escapes
            lambda s: re.sub(r'([\x00-\x08\x0e-\x1f\x7f])', self._format_control_char, s)
        )

        self._filters_fixed = [
            self._filter_sgr, self._filter_nf, self._filter_esq, self._filter_control
        ]
        self._filters_post = [

        ]

        self._control_char_map = ConfidentDict({
            k: FormatRegistry.get_control_marker(k) for k in self.CONTROL_CHARCODES
        })

    @abc.abstractmethod
    def get_fallback_char(self) -> AnyStr:
        pass

    @abc.abstractmethod
    def format(self, raw_input: Union[AnyStr, List[AnyStr]], offset: int):
        pass

    def _add_marker_match(self, mm: MarkerMatch):
        return

    def _process_input(self, decoded_input: str) -> str:
        return apply_filters(decoded_input, *self._filters_fixed)

    def _postprocess_input(self, decoded_input: str) -> str:
        return apply_filters(decoded_input, *self._filters_post)

    def _filter_sgr_param(self, p):
        return len(p) > 0 and p != '0'

    @abc.abstractmethod
    def _format_csi_sequence(self, match: Match) -> AnyStr:
        pass

    def _format_generic_escape_sequence(self, match: Match) -> AnyStr:
        if Settings.ignore_control:
            return self.get_fallback_char() + match.group(0)

        introducer = match.group(1)
        info = ''
        if Settings.effective_info_level() >= 1:
            info = introducer
        if Settings.effective_info_level() >= 2:
            info = match.group(0)
        # if introducer == ' ':
        #    introducer = FormatRegistry.marker_space.marker_char
        charcode = ord(introducer)
        marker = FormatRegistry.get_esq_marker(charcode)
        return marker.print() + info

    def _format_control_char(self, match: Match) -> AnyStr:
        if Settings.ignore_control:
            return self.get_fallback_char()
        charcode = ord(match.group(0))
        marker = self._control_char_map.require_or_die(charcode)
        self._add_marker_match(MarkerMatch(match, marker))
        return marker.print()


class TextFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        super().__init__(_writer)
        self._whitespace_map = {
            0x09: FormatRegistry.marker_tab.print(),
            0x0b: FormatRegistry.marker_vert_tab.print(),
            0x0c: FormatRegistry.marker_form_feed.print(),
            0x0d: FormatRegistry.marker_car_return.print(),
            0x0a: FormatRegistry.marker_newline.print() + '\x0a',  # actual newline
            0x20: FormatRegistry.marker_space.print(),
        }

    def get_fallback_char(self) -> AnyStr:
        return ''

  #  def _postprocess(self, processed_input: str) -> str:
        #if Settings.include_space:
        #    processed_input = re.sub(
        #        r'(\x20+)',
        #        lambda m: MarkerWhitespace.sget_fmt()(m.group(1)),
        #        processed_input
        #    )
        #    processed_input = re.sub(r'\x20', FormatRegistry.marker_space.marker_char, processed_input)
        #return processed_input

    def format(self, raw_input: Union[str, List[str]], offset: int):
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = self._postprocess_input(
                self._process_input(raw_input_line)
            )

            if Settings.no_line_numbers:
                prefix = ''
            else:
                prefix = fmt_green('{0:2d}'.format(offset + 1)) + fmt_cyan('│')

            formatted_input = prefix + processed_input
            aligned_raw_input = (apply_filters(prefix, ReplaceSGRSequences(''))) + raw_input_line

            self._writer.write_line(formatted_input, aligned_raw_input)
            offset += 1

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        introducer = match.group(1)  # e.g. '['
        params = match.group(2)  # e.g. '1;7'
        terminator = match.group(3)  # e.g. 'm'

        params_splitted = re.split(r'[^0-9]+', params)
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        if Settings.ignore_esc:
            if terminator == SGRSequence.TERMINATOR and not Settings.no_color_content:
                return SGRSequence(*params_values).str
            return ''

        info = ''
        if Settings.effective_info_level() >= 1:
            info += SGRSequence.SEPARATOR.join(params_values)
        if Settings.effective_info_level() >= 2:
            info = introducer + info + terminator

        if terminator == SGRSequence.TERMINATOR:
            if len(params_values) == 0:
                return FormatRegistry.marker_sgr_reset.print()
            return FormatRegistry.marker_sgr.print(info, SGRSequence(*params_values))
        else:
            return FormatRegistry.marker_esc_csi.print(info)


class MarkerMatch:
    def __init__(self, match: Match, marker: Marker = None, overwrite: bool = False):
        self.match = match
        self.fmt = None
        self.marker_char = None
        if marker:
            self.set_marker(marker)

        self.overwrite = overwrite
        self.sgr_seq = None
        self.applied: bool = False

    def set_marker(self, marker: Marker):
        self.fmt = marker.get_fmt()
        self.marker_char = marker.marker_char

    def _format(self, source_text: str) -> str:
        if self.fmt is None:
            return source_text
        return self.fmt(source_text)

    def target_text_hex(self, source_text: str) -> str:
        return self._format(source_text)

    def target_text_processed(self, source_text: str) -> str:
        if self.overwrite:
            target_text = self._format(self.marker_char if self.marker_char else '?')
        else:
            target_text = self._format(source_text)

        if self.sgr_seq and not Settings.no_color_content:
            target_text += self.sgr_seq + MarkerSGR.PROHIBITED_CONTENT_SEQS.str

        return target_text


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
            k: FormatRegistry.get_control_marker(k, 1) for k in self.CONTROL_CHARCODES
        })

        self._whitespace_map = {
            '\t': MarkerWhitespace(FormatRegistry.marker_tab.marker_char[0]),
            '\v': FormatRegistry.marker_vert_tab,
            '\f': FormatRegistry.marker_form_feed,
            '\r': FormatRegistry.marker_car_return,
            '\n': FormatRegistry.marker_newline,
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
            merged_row = '{}{}{}'.format(
                self._print_offset(offset),
                hex_row + RESET.str + self.PADDING_SECTION,
                postprocessed_row + RESET.str,
            )
            if is_guide_row:
                merged_row = FormatRegistry.fmt_nth_row_col(merged_row)

            self._writer.write_line(merged_row + '\n')
            self._row_num += 1

            offset += len(raw_row)
            local_min_pos += len(raw_row)
            self._buffer_raw = self._buffer_raw[len(raw_row):]
            buffer_processed = buffer_processed[len(raw_row):]  # should be equal

        if len(raw_input) == 0:
            self._writer.write_line(self._print_offset(offset, True) + '\n')

    def _format_offset(self, offset: int) -> AnyStr:
        return '{:08x}{}'.format(offset, self.PADDING_SECTION)

    def _print_offset(self, offset: int, is_total: bool = False):
        fmt = fmt_green
        if is_total:
            fmt = Format(HI_BLUE)
        return re.sub(r'^(0+)(\S+)(\s)', fmt(DIM.str + r'\1' + DIM_BOLD_OFF.str + r'\2') + fmt_cyan('│'),
                      self._format_offset(offset))

    def _add_marker_match(self, fsegment: MarkerMatch): # @todo formatted segment
        self._process_matches.append(fsegment)

    def _decode_and_process(self, raw_input: bytes, cols: int) -> AnyStr:
        decoded = raw_input.decode(errors='replace').replace('\ufffd', self.FALLBACK_CHAR)
        # if Settings.OVERLAY_GRID and not is_guide_row:
        #    formatted = re.sub('(.)(.{,7})', FormatRegistry.fmt_first_chunk_col('\\1') + '\\2', formatted)
        processed = self._process_input(decoded)
        sanitized = apply_filters(processed,
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
                chunks_x2[i] = re.sub(r'^(..)', FormatRegistry.fmt_first_chunk_col(r'\1'), chunk_x2)

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
                marker = FormatRegistry.marker_sgr_reset
            else:
                marker = FormatRegistry.marker_sgr
            mmatch.sgr_seq = SGRSequence(*params_values).str
        else:
            marker = FormatRegistry.marker_esc_csi

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


class CustomHelpFormatter(HelpFormatter):
    INDENT_INCREMENT = 2
    INDENT = ' ' * INDENT_INCREMENT

    @staticmethod
    def format_header(title: str) -> str:
        return fmt_bold(title.upper())

    def __init__(self, prog):
        super().__init__(prog, max_help_position=30, indent_increment=self.INDENT_INCREMENT)

    def start_section(self, heading: Optional[str]) -> None:
        super().start_section(self.format_header(heading))

    def add_usage(self, usage: Optional[str], actions: Iterable[Action], groups: Iterable,
                  prefix: Optional[str] = ...) -> None:
        super().add_text(self.format_header('usage: '))
        super().add_usage(usage, actions, groups, prefix=self.INDENT)

    def add_examples(self, examples: List[str]):
        self.start_section('example{}'.format('s' if len(examples) > 1 else ''))
        self._add_item(self._format_text, ['\n'.join(examples)])
        self.end_section()

    def _format_action_invocation(self, action):
        # same as in superclass, but without printing argument for short options
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            parts = []
            if action.nargs == 0:
                parts.extend(action.option_strings)
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    if len(option_string) > 2 or len(action.option_strings) == 1:
                        parts.append('%s %s' % (option_string, args_string))
                    else:
                        parts.append(option_string)

            return ', '.join(parts)

    def _format_text(self, text: str) -> str:
        return super()._format_text(text).rstrip('\n') + '\n'

    def _fill_text(self, text, width, indent):
        return ''.join(indent + line for line in text.splitlines(keepends=True))


class CustomArgumentParser(ArgumentParser):
    def __init__(self, examples: List[str] = None, epilog: List[str] = None, **kwargs):
        self.examples = examples
        kwargs.update({'epilog': '\n'.join(epilog)})
        super(CustomArgumentParser, self).__init__(**kwargs)

    def format_help(self) -> str:
        formatter = self._get_formatter()
        if self.epilog:
            formatter.add_text(' ')
            formatter.add_text(self.epilog)
        if self.examples and isinstance(formatter, CustomHelpFormatter):
            formatter.add_examples(self.examples)

        ending_formatted = formatter.format_help()
        self.epilog = None

        result = super().format_help() + ending_formatted
        result = re.sub(r'(\033\[[0-9;]*m)?\s*:\s*(\n|\033|$)', r'\1\2', result)
        return result


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
        self._parse_args()
        if Settings.legend:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'colombo-legend.ansi'), 'rt') as f:
                print(f.read())
                exit(0)

        Colombo.BINARY_MODE = Settings.binary

        writer = Writer()
        if self.BINARY_MODE:
            reader = BinaryReader(Settings.filename, BinaryFormatter(writer))
        else:
            reader = TextReader(Settings.filename, TextFormatter(writer))

        try:
            reader.read()
        except UnicodeDecodeError:
            if not self.BINARY_MODE:
                print('Binary data detected, cannot proceed in text mode')
                print('Use -b option to run in binary mode')
            else:
                raise

    def _parse_args(self):
        parser = CustomArgumentParser(
            description='Escape sequences and control characters visualiser',
            usage='%(prog)s [-t | -b | -l | -h] [<options>] [<file>]',
            epilog=[
                '',
                'Mandatory or optional arguments to long options are also mandatory or optional for any corresponding short options.',
                '', 'Ignore-<class> options are interpreted as follows:',
                CustomHelpFormatter.INDENT + '* In text mode: hide correspondning character class from output completely;',
                CustomHelpFormatter.INDENT + '* In binary mode: print "{}" instead of selected chars and print their hex codes dimmed.'.
                    format(BinaryFormatter.FALLBACK_CHAR),
            ],
            examples=[
                '%(prog)s -i 2 -e --ignore-space file.txt',
                '%(prog)s -b -w16 file.bin',
            ],
            add_help=False,
            formatter_class=lambda prog: CustomHelpFormatter(prog),
        )
        parser.add_argument('filename', metavar='<file>', nargs='?',
                            help='file to read from; if empty or "-", read stdin instead')

        modes_group = parser.add_argument_group('mode selection')
        modes_group_nested = modes_group.add_mutually_exclusive_group()
        modes_group_nested.add_argument('-t', '--text', action='store_true', default=True,
                                        help='open file in text mode (this is the default)')
        modes_group_nested.add_argument('-b', '--binary', action='store_true', default=False,
                                        help='open file in binary mode')
        modes_group_nested.add_argument('-l', '--legend', action='store_true', default=False,
                                        help='show annotation symbol list and exit')
        modes_group_nested.add_argument('-h', '--help', action='help', default=SUPPRESS,
                                        help='show this help message and exit')

        generic_group = parser.add_argument_group('generic options')
        esc_output_group = generic_group.add_mutually_exclusive_group()
        space_output_group = generic_group.add_mutually_exclusive_group()
        control_output_group = generic_group.add_mutually_exclusive_group()
        esc_output_group.add_argument('-e', '--focus-esc', action='store_true', default=False,
                                      help='highlight escape sequences markers')
        space_output_group.add_argument('-s', '--focus-space', action='store_true', default=False,
                                        help='highlight whitespace markers')
        control_output_group.add_argument('-c', '--focus-control', action='store_true', default=False,
                                          help='highlight control char markers')
        esc_output_group.add_argument('-E', '--ignore-esc', action='store_true', default=False,
                                      help='ignore escape sequences')
        space_output_group.add_argument('-S', '--ignore-space', action='store_true', default=False,
                                        help='ignore whitespaces')
        control_output_group.add_argument('-C', '--ignore-control', action='store_true', default=False,
                                          help='ignore control chars')
        generic_group.add_argument('--no-color-content', action='store_true', default=False,
                                   help='disable applying input file formatting to the output')

        text_mode_group = parser.add_argument_group('text mode only')
        text_mode_group.add_argument('-i', '--info', metavar='<level>', action='store', type=int, default=1,
                                     help='escape sequence marker verbosity (0-2, default %(default)s)')
        text_mode_group.add_argument('-L', '--max-lines', metavar='<num>', action='store', type=int, default=0,
                                     help='stop after reading <num> lines')
        text_mode_group.add_argument('--no-line-numbers', action='store_true', default=False,
                                     help='do not print line numbers')
        text_mode_group.add_argument('--no-color-markers', action='store_true', default=False,
                                     help='disable applying input file formatting to SGR markers')
        text_mode_group.add_argument('--pipe-stderr', action='store_true', default=False,
                                     help='send raw input lines to stderr along with default output')

        bin_mode_group = parser.add_argument_group('binary mode only')
        bin_mode_group.add_argument('-B', '--max-bytes', metavar='<num>', action='store', type=int, default=0,
                                    help='stop after reading <num> bytes')
        bin_mode_group.add_argument('-w', '--columns', metavar='<num>', action='store', type=int, default=0,
                                    help='format output as <num>-columns wide table (default %(default)s = auto)')
        bin_mode_group.add_argument('-g', '--grid', action='store_true', default=False,
                                    help='overlay byte table with 8x8')

        return parser.parse_args(namespace=Settings)


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
