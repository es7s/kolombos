#!/usr/bin/env python3

from __future__ import annotations

import abc
import os
import re
import sys
import traceback
from argparse import Namespace
from enum import Enum
from functools import reduce
from typing import IO, AnyStr, Optional, List, Union


# ------------------------------------------------------------------------------
# echo "   ______      __                __"
# echo "  / ____/___  / /___  ____ ___  / /_  ____"
# echo " / /   / __ \/ / __ \/ __ '__ \/ __ \/ __ \ "
# echo "/ /___/ /_/ / / /_/ / / / / / / /_/ / /_/ /"
# echo "\____/\____/_/\____/_/ /_/ /_/_.___/\____/"

# _cs 48 05 26


class SGRParam(Enum):
    RESET = 0
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
    WHITE = 37

    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGNETA = 45
    BG_CYAN = 46
    BG_WHITE = 47

    GRAY = 90
    HI_RED = 91
    HI_GREEN = 92
    HI_YELLOW = 93
    HI_BLUE = 94
    HI_MAGNETA = 95
    HI_CYAN = 96
    HI_WHITE = 97

    TEXT_COLOR_OFF = 39
    BG_COLOR_OFF = 49


class Sequence:
    _payload: AnyStr

    def __init__(self, payload: AnyStr):
        self._payload = payload

    def __str__(self):
        return self._payload

    def __add__(self, other: Sequence) -> Sequence:
        return Sequence(self._payload + (str(other)))


class SGRSequnce(Sequence):
    _INTRODUCER = '\033['
    _TERMINATOR = 'm'

    def __init__(self, params_raw: Union[int, Enum[int], str, List]):
        super().__init__(self._build_sgr_sequence(params_raw))

    def _build_sgr_sequence(self, params_raw: Union[int, Enum[int], str, List]) -> AnyStr:
        return '{}{}{}'.format(self._INTRODUCER, ';'.join(self._normalize_params(params_raw)), self._TERMINATOR)

    def _normalize_params(self, params_raw: Union[int, SGRParam, str, List]) -> List[str]:
        if type(params_raw) is list:
            norm_params = params_raw
        else:
            norm_params = [params_raw]

        norm_params = list(map(self._map_param, norm_params))
        norm_params = list(filter(lambda p: len(p) > 0 and p != '0', norm_params))
        return norm_params

    def _map_param(self, param_raw: Union[int, SGRParam, str]) -> AnyStr:
        if type(param_raw) in (int, str):
            return str(param_raw)
        elif type(param_raw) is SGRParam:
            return str(param_raw.value)
        raise RuntimeError("Illegal seq param type {}".format(type(param_raw)))


class SequenceEnclosing:
    _lead: Sequence
    _paloyad: AnyStr
    _trail: Optional[Sequence]

    def __init__(self, lead: Sequence, trail: Optional[Sequence] = None, value: AnyStr = None):
        self._lead = lead
        self._trail = trail
        self._payload = value

    def wrap(self, payload_override: Optional[AnyStr] = None) -> AnyStr:
        if payload_override:
            return self.open + payload_override + self.close
        if self._payload:
            return self.open + self._payload + self.close
        return self.open + self.close

    @property
    def open(self):
        return str(self._lead)

    @property
    def close(self):
        return str(self._trail) if self._trail else ''


class PyTermor:
    RESET = SGRSequnce(SGRParam.RESET)
    TEXT_COLOR_OFF = SGRSequnce(SGRParam.TEXT_COLOR_OFF)

    dim = SequenceEnclosing(SGRSequnce(SGRParam.DIM), SGRSequnce(SGRParam.DIM_BOLD_OFF))
    inverse = SequenceEnclosing(SGRSequnce(SGRParam.INVERSED), SGRSequnce(SGRParam.INVERSED_OFF))
    underline = SequenceEnclosing(SGRSequnce(SGRParam.UNDERLINED), SGRSequnce(SGRParam.UNDERLINED_OFF))
    overline = SequenceEnclosing(SGRSequnce(SGRParam.OVERLINED), SGRSequnce(SGRParam.OVERLINED_OFF))
    red = SequenceEnclosing(SGRSequnce(SGRParam.RED), TEXT_COLOR_OFF)
    yellow = SequenceEnclosing(SGRSequnce(SGRParam.YELLOW), TEXT_COLOR_OFF)
    green = SequenceEnclosing(SGRSequnce(SGRParam.GREEN), TEXT_COLOR_OFF)
    cyan = SequenceEnclosing(SGRSequnce(SGRParam.CYAN), TEXT_COLOR_OFF)
    gray = SequenceEnclosing(SGRSequnce(SGRParam.GRAY), TEXT_COLOR_OFF)


class Writer:
    _f: IO

    def __init__(self):
        self._f = sys.stdout

    def write_line(self, formatted_line):
        self._f.write(formatted_line)


class AbstractFormatter:
    pass


class Formatter(AbstractFormatter):
    _writer: Writer

    _excluded_content_output_sgr_params: list = list(map(lambda v: str(v.value), [
        SGRParam.RESET, SGRParam.INVERSED, SGRParam.INVERSED_OFF
    ]))
    _unknown_esq_marker: SequenceEnclosing = \
        SequenceEnclosing(SGRSequnce([SGRParam.BG_BLACK, SGRParam.HI_YELLOW, SGRParam.INVERSED]), PyTermor.RESET)

    def __init__(self, _writer: Writer):
        self._writer = _writer

    def format(self, raw_input, offset):
        if type(raw_input) is str or type(raw_input) is list:
            self._format_text(raw_input, offset)
        elif type(raw_input) is bytes:
            self._format_binary(raw_input, offset)
        else:
            raise NotImplementedError(type(raw_input))

    def _format_text(self, raw_input: Union[str, List[str]], offset: int):
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = raw_input_line.translate({
                0x20: '\u2423',
                0x0a: PyTermor.gray.open + PyTermor.inverse.wrap('\u21b5') + str(PyTermor.TEXT_COLOR_OFF) + '\u000a',
                0x00: PyTermor.red.wrap('\u00d8'),
                0x1b: '\0',
            })
            # expandtabs
          #  pr/    ocessed_input = re.sub(
          #       '\0(\\[[0;]*m)',
          #       PyTermor.inverse.wrap('Ǝ') + '\033\\1',
          #       processed_input
          #  )
            processed_input = re.sub(
                '\0\\[([0-9:;<=>?])([0-9;]*)([@A-Z\\[\\]^_`a-z{|}~])',
                self._format_escape_sequence,
                processed_input
            )
        #    processed_input = re.sub(
         #       '(\0)(\\[[;0-9]+m)',
         #       '\033\\2' + PyTermor.inverse.wrap('ɘ') + '\\2' +  str(PyTermor.RESET),
         #       processed_input
         #   )
         #   processed_input = re.sub(
        #      '(\0)(\\[[;0-9]+m)',
        #       str(PyTermor.reset) + PyTermor.inverse.open + PyTermor.gray('ɘ') + '\033\\2' + '\\2' + str(PyTermor.reset),
        #       processed_input
        #   )
            processed_input = re.sub('\0', self._unknown_esq_marker.wrap('ɘ'), processed_input)

            formatted_input = "{}{} ".format(
                PyTermor.green.wrap(str(offset + 1)),
                PyTermor.cyan.wrap(':')
            ) + processed_input

            self._writer.write_line(formatted_input)
            offset += 1

    def _format_escape_sequence(self, match) -> AnyStr:
        esq_match = match.group(1)
        esq_params_splitted = re.split('[^0-9]+', esq_match)
        esq_params = list(filter(lambda p: p and
                                           len(p) > 0 and
                                           p not in Formatter._excluded_content_output_sgr_params,
                                 esq_params_splitted))

        if len(esq_params) == 0:
            return PyTermor.inverse.wrap('Ǝ') + str(PyTermor.RESET)

        for i, v in enumerate(esq_params):
            if i % 2 == 0:
                esq_params[i] = PyTermor.underline.wrap(v)
            else:
                esq_params[i] = PyTermor.overline.wrap(v)

        return PyTermor.inverse.wrap('ɘ') + \
               ('\033' + esq_match) + \
               ''.join(esq_params) + \
               str(PyTermor.RESET)

    def _process_esq(self, m):
        esq = m.group(1)
        esq_params = list(filter(lambda p: p, re.split('[^0-9]', esq)))
        esq_params_packed = ''.join([p +( PyTermor.underline.open if i % 2 == 0 else PyTermor.underline.close) for i, p in enumerate(esq_params)])
        return PyTermor.inverse.wrap('ɘ')+   '\033' + esq + ''.join(esq_params_packed )+ str(PyTermor.RESET)

    def _format_binary(self, raw_input: bytes, offset: int):
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
    _args: Namespace

    def run(self):
        try:
            self._invoke()
        except Exception as e:
            self._handle(e)
        exit(0)

    def _invoke(self):
        # parse args
        writer = Writer()
        reader = TextReader(
            sys.argv[1] if len(sys.argv) > 1 else None,
            Formatter(writer)
        )
        reader.read()

    def _handle(self, e: Exception):
        # if self.args.verbose:
        self._log_traceback(e)  # TODO logging
        print(str(e), file=sys.stderr)
        exit(1)

    def _log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n') for line in traceback.format_exception(e.__class__, e, ex_traceback)]
        print("\n".join(tb_lines), file=sys.stderr)


if __name__ == '__main__':
    Colombo().run()
