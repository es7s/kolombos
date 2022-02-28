#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
import traceback
from argparse import Namespace
from enum import Enum
from typing import IO, AnyStr, Optional, List, Union

# ------------------------------------------------------------------------------
# echo "   ______      __                __"
# echo "  / ____/___  / /_  ______ ___  / /_  ____"
# echo " / /   / __ \/ / / / / __ '__ \/ __ \/ __ \ "
# echo "/ /___/ /_/ / / /_/ / / / / / / /_/ / /_/ /"
# echo "\____/\____/_/\__,_/_/ /_/ /_/_.___/\____/"

#_cs 48 05 26


class SgrParam(Enum):
    BOLD = 1
    DIM = 2
    ITALIC = 3
    UNDERLINED = 4
    BLINK_SLOW = 5
    BLINK_FAST = 6
    INVERSED = 7
    HIDDEN = 8
    CROSSLINED = 9
    UNDERLINED_X2 = 21
    OVERLINED = 53

    DIM_BOLD_OFF = 22
    ITALIC_OFF = 23
    UNDERLINED_OFF = 24
    BLINK_OFF = 25
    INVERSED_OFF = 27
    HIDDEN_OFF = 28
    CROSSLINED_OFF = 29
    OVERLINED_OFF = 55

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGNETA = 35
    CYAN = 36
    GRAY = 37

    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGNETA = 45
    BG_CYAN = 46
    BG_GRAY = 47

    HI_RED = 91
    HI_GREEN = 92
    HI_YELLOW = 93
    HI_BLUE = 94
    HI_MAGNETA = 95
    HI_CYAN = 96
    HI_GRAY = 97

    TEXT_COLOR_OFF = 39
    BG_COLOR_OFF = 49


class Sequence:
    _payload: AnyStr

    def __init__(self, payload: AnyStr):
        self._payload = payload

    def __str__(self):
        return self._payload


class SgrSequnce(Sequence):
    _INTRODUCER = '\033['
    _TERMINATOR = 'm'

    def __init__(self, params_raw: Union[int, Enum[int], str, List]):
        norm_params = self.__normalize_params(params_raw)
        encoded_params = self.__encode_params(norm_params)
        super().__init__(self.__build_sgr_sequence(encoded_params))

    def __normalize_params(self, params_raw: Union[int, SgrParam, str, List]) -> List[str]:
        if type(params_raw) is list:
            norm_params = params_raw
        else:
            norm_params = [params_raw]

        norm_params = list(map(self.__map_param, norm_params))
        norm_params = list(filter(lambda p: len(p) > 0 and p != '0', norm_params))
        return norm_params

    def __map_param(self, param_raw: Union[int, SgrParam, str]) -> AnyStr:
        if type(param_raw) in (int, str):
            return str(param_raw)
        elif type(param_raw) is SgrParam:
            return str(param_raw.value)
        raise RuntimeError("Illegal seq param type {}".format(type(param_raw)))

    def __encode_params(self, norm_params: List[str]) -> str:
        return ';'.join(norm_params)

    def __build_sgr_sequence(self, encoded_params: str) -> AnyStr:
        return '{}{}{}'.format(self._INTRODUCER, encoded_params, self._TERMINATOR)


class SequenceEnclosing:
    _lead: Sequence
    _trail: Optional[Sequence]

    def __init__(self, lead: Sequence, trail: Optional[Sequence]):
        self._lead = lead
        self._trail = trail

    def open(self) -> AnyStr:
        return str(self._lead)

    def close(self) -> AnyStr:
        return str(self._trail) if self._trail else ''

    def wrap(self, payload: str) -> AnyStr:
        return self.open() + payload + self.close()

    def wrap_hard(self, payload: str) -> AnyStr:
        return self.open() + payload + SequenceRegistry.RESET


class SequenceRegistry:
    RESET = str(SgrSequnce(0))
    TEXT_COLOR_OFF = SgrSequnce(SgrParam.TEXT_COLOR_OFF)

    inverse = SequenceEnclosing(SgrSequnce(SgrParam.INVERSED), SgrSequnce(SgrParam.INVERSED_OFF))
    red = SequenceEnclosing(SgrSequnce(SgrParam.RED), TEXT_COLOR_OFF)
    green = SequenceEnclosing(SgrSequnce(SgrParam.GREEN), TEXT_COLOR_OFF)
    cyan = SequenceEnclosing(SgrSequnce(SgrParam.CYAN), TEXT_COLOR_OFF)



class AppMode(Enum):
    TEXT = "TEXT"
    BINARY = "BINARY"


class Writer:
    _f: IO

    def __init__(self):
        self._f = sys.stdout

    def write_line(self, formatted_line):
        self._f.write(formatted_line)


class Formatter:
    _writer: Writer
    _copty: SequenceRegistry

    def __init__(self, _writer: Writer):
        self._writer = _writer
        self._copty = SequenceRegistry()

    def format(self, raw_input, offset):
        if type(raw_input) is str or type(raw_input) is list:
            self.__format_text(raw_input, offset)
        elif type(raw_input) is bytes:
            self.__format_binary(raw_input, offset)
        else:
            raise NotImplementedError(type(raw_input))

    def __format_text(self, raw_input: Union[str, List[str]], offset: int):
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = raw_input_line.translate({
                0x20: 0x2423,
                0x00: self._copty.red.wrap('\u00d8'),
                0x0a: self._copty.inverse.wrap('\u21b5') + '\u000a',
                0x1b: self._copty.inverse.wrap('ɘ') + '\033',
            })

            formatted_input = "{}{} ".format(
                self._copty.green.wrap(str(offset + 1)),
                self._copty.cyan.wrap(':')
            ) + processed_input

            self._writer.write_line(formatted_input)
            offset += 1

    def __format_binary(self, raw_input: bytes, offset: int):
        processed_line_hex = raw_input.hex(" ")
        print(processed_line_hex)

class Reader:
    _filename: Optional[str]
    _f : Optional
    _mode: AppMode
    _formatter: Formatter
    _read_chunk_size: int

    def __init__(self, filename: Optional[str], formatter: Formatter):
        self._filename = filename
        self._formatter = formatter

    def read(self, mode: AppMode):
        try:
            self.__open(mode)
            if self._f.seekable():
                self._f.seek(0)
            if mode == AppMode.TEXT:
                while raw_input := self._f.readlines(1): # @ReFACtrOR
                    self._formatter.format(raw_input, self._offset)
                    self._offset += len(raw_input)
            elif mode == AppMode.BINARY:
                while raw_input := self._f.read(1024): # @ReFACtrOR
                    self._formatter.format(raw_input, self._offset)
                    self._offset += len(raw_input)
        finally:
            self.__close()

    def __open(self, mode: AppMode):  # @ReFACtrOR
        self._offset = 0
        if mode == AppMode.TEXT:
            self._read_chunk_size = 1
            if self._filename:
                self._f = open(self._filename, 'rt', newline=os.linesep)
            else:
                self._f = sys.stdin

        elif mode == AppMode.BINARY:
            self._read_chunk_size = 1024
            if self._filename:
                self._f = open(self._filename, 'rb')
            else:
                self._f = sys.stdin.buffer #open(sys.stdin.buffer, 'rb')


    def __close(self):
        if self._f and not self._f.closed:
            self._f.close()


class App:
    _args: Namespace
    _writer: Writer
    _formatter: Formatter
    _reader: Reader

    def run(self):
        try:
            self.__invoke()
        except Exception as e:
            self.__handle(e)
        exit(0)

    def __invoke(self):
        # parse args
        self._writer = Writer()
        self._formatter = Formatter(self._writer)
        self._reader = Reader(
            sys.argv[1] if len(sys.argv) > 1 else None,
            self._formatter
        )
        try:
            self._reader.read(AppMode.TEXT)
        except UnicodeDecodeError:
            self._reader.read(AppMode.BINARY)

    def __handle(self, e: Exception):
        #if self.args.verbose:
        self.__log_traceback(e)  # TODO logging
        print(str(e), file=sys.stderr)
        exit(1)

    def __log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n') for line in traceback.format_exception(e.__class__, e, ex_traceback)]
        print("\n".join(tb_lines), file=sys.stderr)


if __name__ == '__main__':
    App().run()
