#!/usr/bin/env python3

from __future__ import annotations

import abc
import os
import re
import sys
import traceback
from typing import IO, AnyStr, Optional, List, Union, Match
from pytermor import sanitize
from pytermor.preset import *

# ------------------------------------------------------------------------------
# echo "   ______      __                __"
# echo "  / ____/___  / /___  ____ ___  / /_  ____"
# echo " / /   / __ \/ / __ \/ __ '__ \/ __ \/ __ \ "
# echo "/ /___/ /_/ / / /_/ / / / / / / /_/ / /_/ /"
# echo "\____/\____/_/\____/_/ /_/ /_/_.___/\____/"

# _cs 48 05 26


class Writer:
    def __init__(self):
        self._io_primary: IO = sys.stdout
        self._io_support: IO = sys.stderr

    def write_line(self, output_line: AnyStr, helper_line: AnyStr):
        self._io_primary.write(output_line)

        if Colombo.ORIGINAL_STDERR:
            self._io_support.write(helper_line)
            self._io_support.write('-' * 80 + '\n')
            self._io_primary.flush()
            self._io_support.flush()


class AbstractFormatter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def format(self, raw_input: Union[AnyStr, List[AnyStr]], offset: int):
        pass


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


class MarkerWhitespace(Marker):
    fmt = Format(DIM, DIM_BOLD_OFF)
    fmt_focused = Format(BOLD + BG_BLUE + BLACK, reset=True)

    def __init__(self, marker_char: str, marker_char_focused_override: Optional[str] = None):
        super().__init__(marker_char)
        self._marker_char_focused = marker_char_focused_override if marker_char_focused_override else marker_char

    def print(self):
        if Colombo.FOCUS_WHITESPACE:
            return self.fmt_focused(self.marker_char)
        return self.fmt(self.marker_char)

    @property
    def marker_char(self) -> str:
        if Colombo.FOCUS_WHITESPACE:
            return self._marker_char_focused
        return self._marker_char

class MarkerEscapeSeq(Marker):
    def __init__(self, marker_char: str, opening_seq: SGRSequence):
        super().__init__(marker_char)
        self._fmt = Format(opening_seq + OVERLINED, reset=True)
        self._fmt_focused = Format(opening_seq + INVERSED + BG_BLACK, reset=True)

    def print(self, additional_info: str = ''):
        fmt = self._fmt_focused if Colombo.FOCUS_CONTROL_SEQUENCE else self._fmt
        return RESET.str + fmt(self._marker_char + additional_info)


class SGRMarker(Marker):
    def __init__(self, marker_char: str):
        super().__init__(marker_char)

    def print(self, additional_info: str = '', seq: SGRSequence = None):
        marker_seq = HI_WHITE + BG_BLACK
        if Colombo.FOCUS_CONTROL_SEQUENCE:
            info_seq = INVERSED
            if Colombo.SGR_INFO_COLORIZING:
                info_seq += OVERLINED
        else:
            info_seq = OVERLINED
        marker_seq += info_seq

        result = RESET.str
        if Colombo.SGR_INFO_COLORIZING:
            result += marker_seq.str + self._marker_char + seq.str + BLINK_OFF.str + info_seq.str + additional_info
        else:
            result += marker_seq.str + self._marker_char + additional_info + seq.str

        if Colombo.CONTENT_DIRECT_COLORIZING:
            # even though we allow to colorize content, we'll explicitly disable any inversion and overline
            #  effect to guarantee that the only inversed and/or overlined things on the screen are our markers
            # also disable blinking
            result += BG_COLOR_OFF.str + INVERSED_OFF.str + OVERLINED_OFF.str + BLINK_OFF.str  # ... content
        else:
            result += RESET.str  # ... content
        return result


class TextFormatRegistry:
    import pytermor

    tpl_marker_ascii_ctrl = Marker.make('χ{}', INVERSED + RED)
    marker_null = Marker.make('Ø', INVERSED + HI_RED)
    marker_bell = Marker.make('Ɐ', INVERSED + YELLOW)
    marker_backspace = Marker.make('⇇', INVERSED + HI_YELLOW)
    marker_delete = Marker.make('⇉', INVERSED + HI_YELLOW)
    # 0x80-0x9f: UCC (binary mode only)

    marker_tab = MarkerWhitespace('⇥\t')  # →
    marker_space = MarkerWhitespace('␣', '·') #HI_BLUE + BG_BLACK)
    marker_newline = MarkerWhitespace('↵')
    marker_vert_tab = MarkerWhitespace('⤓') # , MAGENTA)  # ↓
    marker_form_feed = MarkerWhitespace('↡') #, MAGENTA)
    marker_car_return = MarkerWhitespace('⇤') #, MAGENTA)

    marker_sgr_reset = MarkerEscapeSeq('ϴ', pytermor.build_text256_seq(231))
    marker_sgr = SGRMarker('ǝ')
    marker_esc_csi = MarkerEscapeSeq('Ͻ', HI_CYAN)
    marker_esc_nf = MarkerEscapeSeq('ꟻ', HI_MAGENTA)
    marker_escape = MarkerEscapeSeq('Ǝ', HI_YELLOW)


class TextFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        self._writer = _writer

    def format(self, raw_input: Union[str, List[str]], offset: int):
        from pytermor.preset import fmt_green, fmt_cyan
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            translation_map = {
                0x00: TextFormatRegistry.marker_null,
                0x07: TextFormatRegistry.marker_bell,
                0x08: TextFormatRegistry.marker_backspace,
                0x09: TextFormatRegistry.marker_tab.print(),
                0x0b: TextFormatRegistry.marker_vert_tab.print(),
                0x0c: TextFormatRegistry.marker_form_feed.print(),
                0x0d: TextFormatRegistry.marker_car_return.print(),
                0x0a: TextFormatRegistry.marker_newline.print() + '\x0a',  # actual newline
                0x1b: '\0',
                0x7f: TextFormatRegistry.marker_delete,
            }

            for i in (list(range(0x01, 0x07)) + list(range(0x0e, 0x20))):
                if i == 0x1b:
                    continue
                translation_map[i] = TextFormatRegistry.tpl_marker_ascii_ctrl.format(re.sub('0x0?', '', hex(i)))
            processed_input = raw_input_line.translate(translation_map)#.expandtabs(4)
            # @TODO expandtabs

            processed_input = re.sub(  # CSI sequences
                '\0(\\[)([0-9;:<=>?]*)([@A-Za-z\\[])',  # group 3 : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
                self._format_csi_sequence,
                processed_input
            )
            processed_input = re.sub(  # nF Escape sequences
                '\0([\x20-\x2f]+)([\x30-\x7e])',
                lambda m: self._format_generic_escape_sequence(m, TextFormatRegistry.marker_esc_nf),
                processed_input,
            )
            processed_input = re.sub(  # other escape sequences
                '\0(.)()',  # group 1 : 0x20-0x7E
                lambda m: self._format_generic_escape_sequence(m, TextFormatRegistry.marker_escape),
                processed_input
            )
            processed_input = re.sub(
               '(\x20+)',
               lambda m: MarkerWhitespace.fmt(m.group(1)),
               processed_input
            )
            processed_input = re.sub('\x20', TextFormatRegistry.marker_space.print(), processed_input)

            line_no = ''
            if Colombo.LINE_NUMBERS:
                fmt_green('{0:2d}'.format(offset + 1)) + fmt_cyan('\u2502')

            formatted_input = line_no + processed_input
            aligned_raw_input = (sanitize(line_no)) + raw_input_line

            self._writer.write_line(formatted_input, aligned_raw_input)
            offset += 1

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        introducer = match.group(1)  # e.g. '['
        params = match.group(2)  # e.g. '1;7'
        terminator = match.group(3)  # e.g. 'm'

        params_splitted = re.split('[^0-9;:<=>?]+', params)
        params_values = list(filter(lambda p: len(p) > 0 and p != '0', params_splitted))

        info = ''
        if Colombo.ESQ_INFO_LEVEL >= 1:
            info += SGRSequence.SEPARATOR.join(params_values)
        if Colombo.ESQ_INFO_LEVEL >= 2:
            info = introducer + info + terminator

        if terminator == SGRSequence.TERMINATOR:
            if len(params_values) == 0:
                return TextFormatRegistry.marker_sgr_reset.print()
            return TextFormatRegistry.marker_sgr.print(info, SGRSequence(*params_values))
        else:
            return TextFormatRegistry.marker_esc_csi.print(info)

    def _format_generic_escape_sequence(self, match: Match, marker: MarkerEscapeSeq) -> AnyStr:
        introducer = match.group(1)  # e.g. '('
        additional = match.group(2)  # e.g. 'B'
        if introducer == ' ':
            introducer = TextFormatRegistry.marker_space.marker_char
        info = ''
        if Colombo.ESQ_INFO_LEVEL >= 1:
            info += introducer
        if Colombo.ESQ_INFO_LEVEL >= 2:
            info += additional

        return marker.print(info)


class BinaryFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        self._writer = _writer

    def format(self, raw_input: bytes, offset: int):
        processed_line_hex = raw_input.hex(" ")
        print(processed_line_hex)


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

    def _close(self):
        if self._io and not self._io.closed:
            self._io.close()


class TextReader(AbstractReader):
    _READ_LINES_COUNT: int = 10

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        super().__init__(filename, formatter)

    def _open(self) -> None:
        if self._filename:
            self._io = open(self._filename, 'rt')
        else:
            self._io = sys.stdin

    def _read_loop(self) -> None:
        while raw_input := self._io.readlines(TextReader._READ_LINES_COUNT):
            self._formatter.format(raw_input, self._offset)
            self._offset += len(raw_input)


class BinaryReader(AbstractReader):
    _READ_CHUNK_SIZE: int = 1024

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        super().__init__(filename, formatter)

    def _open(self) -> None:
        if self._filename:
            self._io = open(self._filename, 'rb')
        else:
            self._io = sys.stdin.buffer

    def _read_loop(self) -> None:
        while raw_input := self._io.read(BinaryReader._READ_CHUNK_SIZE):
            self._formatter.format(raw_input, self._offset)
            self._offset += len(raw_input)


class Colombo:
    ORIGINAL_STDERR = os.environ.get('ORIGINAL_STDERR', False)
    CONTENT_DIRECT_COLORIZING = os.environ.get('CONTENT_DIRECT_COLORIZING', True)
    SGR_INFO_COLORIZING = os.environ.get('SGR_INFO_COLORIZING', True)
    ESQ_INFO_LEVEL = int(os.environ.get('ESQ_INFO_LEVEL', 1))
    FOCUS_CONTROL_SEQUENCE = os.environ.get('FOCUS_CONTROL_SEQUENCE', True)
    FOCUS_WHITESPACE = os.environ.get('FOCUS_WHITESPACE', False)
    LINE_NUMBERS = os.environ.get('LINE_NUMBERS', False)
    VERBOSE = os.environ.get('VERBOSE', True)
    BINARY = False

    def run(self):
        _hanlder = ExceptionHandler()
        try:
            self._invoke()
        except Exception as e:
            _hanlder.handle(e)
        print()
        exit(0)

    def _invoke(self):
        # parse args
        writer = Writer()
        reader = TextReader(
            sys.argv[1] if len(sys.argv) > 1 else None,
            TextFormatter(writer)
        )
        try:
            reader.read()
        except UnicodeDecodeError:
            if not self.BINARY:
                print('Binary data detected, use -b flag to run in binary mode')
            else:
                raise


class ExceptionHandler:
    def __init__(self):
        self.format: Format = fmt_red

    def handle(self, e: Exception):
        if Colombo.VERBOSE:
            self._log_traceback(e)
        else:
            self._write(str(e))
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
