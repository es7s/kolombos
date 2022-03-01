#!/usr/bin/env python3

from __future__ import annotations

import abc
import re
import sys
import traceback
from typing import IO, AnyStr, Optional, List, Union

from pytermor.format import Format
from pytermor.pytermor import PyTermor
from pytermor.sequence import SGRSequence, Preset


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


class TextFormatter(AbstractFormatter):
    _space_marker = Format(Preset.GRAY, Preset.RESET).wrap('\u00b7')  # ·    # 2423 ␣
    _newline_marker = Format(Preset.GRAY, Preset.RESET).wrap('\u21b5')  # ↵
    _null_marker = Format\
        (Preset.INVERSED + Preset.RED)\
        .wrap('\u00d8')  # Ø

    _reset_esq_maker = Format\
        (Preset.RESET + Preset.INVERSED + PyTermor.build_text256_seq(231), Preset.RESET)\
        .wrap('\u018e')  # Ǝ

    _known_esq_marker_format = Format(Preset.INVERSED, Preset.INVERSED_OFF)
    _known_esq_marker = Preset.RESET.str + _known_esq_marker_format.wrap('\u0258')  # ɘ

    _unknown_esq_marker = Format(
        Preset.INVERSED + Preset.HI_YELLOW + Preset.BG_BLACK)\
            .wrap('\u03f4')  # ϴ

    def __init__(self, _writer: Writer):
        self._writer = _writer

    def format(self, raw_input: Union[str, List[str]], offset: int):
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = raw_input_line.translate({
                0x20: self._space_marker, # @TODO OPTIMIZE OMFG
                0x0a: self._newline_marker + '\u000a',  # actual newline
                0x00: self._null_marker,
                0x1b: '\0',
            })
            # @TODO expandtabs
            processed_input = re.sub(
                '\0(\\[)([0-9;:<=>?]*)([@A-Za-z\\[])',  # group 3 : 0x40–0x7E ASCII      @A–Z[\]^_`a–z{|}~
                self._format_escape_sequence,
                processed_input
            )
            processed_input = re.sub('\0', self._unknown_esq_marker, processed_input)

            line_no = PyTermor.green.wrap('{0:2d}'.format(offset + 1)) + \
                      PyTermor.cyan.wrap('\u2502')
            formatted_input = line_no + processed_input
            aligned_raw_input = (PyTermor.sanitize(line_no)) + raw_input_line

            self._writer.write_line(formatted_input, aligned_raw_input)
            offset += 1

    def _format_escape_sequence(self, match) -> AnyStr:
        esq_match = match.group(2)
        esq_params_splitted = re.split('[^0-9]+', esq_match)
        esq_params_values = list(filter(lambda p: len(p) > 0 and p != '0', esq_params_splitted))
        if len(esq_params_values) == 0:
            return self._reset_esq_maker

        if Colombo.ESQ_INFO_LEVEL == 0:
            esq_params_formatted = match.group(3)
        elif Colombo.ESQ_INFO_LEVEL == 1:
            esq_params_formatted = ';'.join(esq_params_values)
        else:
            esq_params_formatted = match.group(1) + ';'.join(esq_params_values) + match.group(3)

        esq_marker = self._known_esq_marker
        esq_marker_params = self._known_esq_marker_format.wrap(esq_params_formatted)
        esq_actual = Format(SGRSequence(*esq_params_values), Preset.RESET)

        if Colombo.CONTENT_DIRECT_COLORIZING:
            # even though we allow to colorize content, we'll explicitly disable any inversion
            # effect to guarantee that the only inversed things on the screen are our markers
            result = esq_marker + esq_marker_params + esq_actual.open + Preset.INVERSED_OFF.str
        else:
            result = esq_marker + esq_actual.open + esq_marker_params + esq_actual.close
        return result


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
    ORIGINAL_STDERR = False
    CONTENT_DIRECT_COLORIZING = True
    ESQ_INFO_LEVEL = 1
    FOCUS_WHITESPACE = False
    VERBOSE = True
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
        self.format: Format = Format(Preset.RED)

    def handle(self, e: Exception):
        if Colombo.VERBOSE:
            self._log_traceback(e)
        else:
            self._write(str(e))
        exit(1)

    def _write(self, s: str):
        print(self.format.wrap(s), file=sys.stderr)

    def _log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n')
                    for line
                    in traceback.format_exception(e.__class__, e, ex_traceback)]
        self._write("\n".join(tb_lines))


if __name__ == '__main__':
    Colombo().run()
