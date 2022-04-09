from __future__ import annotations

import re
from re import Match
from typing import Callable, cast

from pytermor import fmt
from pytermor.util import StringFilter, apply_filters

from kolombo.byteio.parser_buf import ParserBuffer
from . import ReadMode
from .chain import ChainBuffer
from .segment import template
from .segment.template import SegmentTemplateSample
from ..console import Console, printd, ConsoleBuffer
from ..settings import Settings


class Parser:
    def __init__(self, mode: ReadMode, parser_buffer: ParserBuffer, data_flow: ChainBuffer):
        self.F_SEPARATOR = StringFilter[bytes](
            lambda b: re.sub(
                b'('                                   # UTF-8
                b'[\xc2-\xdf][\x80-\xbf]|'             # - non-overlong 2-byte
                b'\xe0[\xa0-\xbf][\x80-\xbf]|'         # - excluding overlongs
                b'[\xe1-\xec\xee\xef][\x80-\xbf]{2}|'  # - straight 3-byte
                b'\xed[\x80-\x9f][\x80-\xbf]|'         # - excluding surrogates
                b'\xf0[\x90-\xbf][\x80-\xbf]{2}|'      # - planes 1-3
                b'[\xf1-\xf3][\x80-\xbf]{3}|'          # - planes 4-15
                b'\xf4[\x80-\x8f][\x80-\xbf]{2}'       # - plane 16
                b')|'
                +
                b'([\x80-\xff]+)|'                     # BINARY DATA
                +                                                             # ESCAPE SEQUENCES
                b'((\x1b)(\x5b)([\x30-\x3f]*)([\x20-\x2f]*)([\x40-\x7e]))|'   # - CSI sequences
                b'((\x1b)([\x20-\x2f])([\x20-\x2f]*)([\x30-\x7e]))|'          # - nF escape sequences
                b'((\x1b)([\x30-\x3f]))|'                                     # - Fp escape sequences
                b'((\x1b)([\x40-\x5f]))|'                                     # - Fe escape sequences
                b'((\x1b)([\x60-\x7e]))|'                                     # - Fs escape sequences
                +                                       # 7-BIT ASCII
                b'([\x00-\x08\x0e-\x1f\x7f]+)|'         # - control chars (incl. standalone escapes \x1b)
                b'([\x09\x0b-\x0d]+)|(\x0a+)|(\x20+)|'  # - whitespaces (\t,\v,\f,\r) | newlines | spaces
                b'([\x21-\x7e]+)',                      # - printable chars (letters, digits, punctuation)
                self._substitute, b
            ))

        self._mode = mode
        self._parser_buffer: ParserBuffer = parser_buffer
        self._chain_buffer: ChainBuffer = data_flow
        self._offset = 0

        self._debug_buffer = Console.register_buffer(ConsoleBuffer(1, 'parser', prefix_fmt=fmt.cyan))
        self._debug_buffer2 = Console.register_buffer(ConsoleBuffer(2, 'parser', prefix_fmt=fmt.cyan))

    def parse(self, buffered_raw_input: bytes, offset: int):
        self._offset = offset
        self._debug_buffer.write(f'Parsing segment: {printd(buffered_raw_input)}')

        unmatched = apply_filters(buffered_raw_input, self.F_SEPARATOR)
        try:
            self._verify(unmatched)
        except AssertionError as e:
            raise RuntimeError(f'Parsing inconsistency at {Console.print_offset(self._offset)}') from e

        self._parser_buffer.crop_raw(unmatched)

    def _substitute(self, m: Match) -> bytes:
        mgroups = {idx: grp for idx, grp in enumerate(m.groups()) if grp}
        primary_mgroup = min(mgroups.keys())
        raw = cast(bytes, m.group(primary_mgroup+1))
        self._debug_print_match_group(primary_mgroup, suboffset=m.start(primary_mgroup + 1))
        self._handle(primary_mgroup, raw)
        return b''

    def _handle(self, mgroup: int, raw: bytes):
        _handler_fn = self._find_handler(mgroup)
        if not _handler_fn:
            raise RuntimeError(f'No handler defined for mgroup {mgroup}: {raw.hex(" ")}')

        sample = _handler_fn(raw)
        self._debug_print_match_sample(raw, sample)
        self._chain_buffer.add(raw, sample)

    def _find_handler(self, mgroup: int) -> Callable[[bytes], SegmentTemplateSample]|None:
        if mgroup == 0:
            return self._handle_utf8_char_bytes
        if mgroup == 1:
            return self._handle_binary_data_bytes
        if mgroup == 2:
            return self._handle_csi_esq_bytes
        if mgroup == 21:
            return self._handle_ascii_control_chars
        if mgroup == 22:
            return self._handle_ascii_whitespace_chars
        if mgroup == 23:
            return self._handle_ascii_newline_chars
        if mgroup == 24:
            return self._handle_ascii_space_chars
        if mgroup == 25:
            return self._handle_ascii_printable_chars
        return None
    
    def _debug_print_match_group(self, mgroup: int, suboffset: int):
        self._debug_buffer2.write(f'Match group #{mgroup:02d}',
                                  offset=(self._offset + suboffset),
                                  end='', flush=False)

    def _debug_print_match_sample(self, raw: bytes, sample: SegmentTemplateSample):
        debug_msg = f'/{sample.template.type_label}: {printd(raw)}'
        debug_processed_bytes = sample.get_processed(len(raw)).encode('ascii', errors="replace")
        if raw != debug_processed_bytes:
            debug_msg += f' -> {printd(debug_processed_bytes)}'
        self._debug_buffer2.write(debug_msg, no_default_prefix=True)

    def _handle_utf8_char_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        if Settings.ignore_utf8:
            return template.T_IGNORED.sample()

        if self._mode == ReadMode.TEXT or Settings.decode:
            decoded = raw.decode('utf8', errors='replace')
            if self._mode == ReadMode.BINARY:
                if len(decoded) < len(raw):
                    decoded = decoded.rjust(len(raw), '_')
                elif len(decoded) > len(raw):
                    decoded = decoded[:len(raw)]
            return template.T_UTF8.sample(decoded)

        return template.T_UTF8.sample()

    def _handle_binary_data_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_csi_esq_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_nf_esq_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_fp_esq_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_fe_esq_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_fs_esq_bytes(self, raw: bytes) -> SegmentTemplateSample: 
        return template.T_TEMP.sample()

    def _handle_ascii_control_chars(self, raw: bytes) -> SegmentTemplateSample: 
        if Settings.ignore_control:
            return template.T_IGNORED.sample()
        return template.T_CONTROL.sample()

    def _handle_ascii_whitespace_chars(self, raw: bytes) -> SegmentTemplateSample: 
        if Settings.ignore_space:
            return template.T_IGNORED.sample()
        return template.T_WHITESPACE.sample()

    def _handle_ascii_newline_chars(self, raw: bytes) -> SegmentTemplateSample: 
        if Settings.ignore_space:
            if self._mode == ReadMode.TEXT:
                return template.T_NEWLINE_TEXT.sample('\n'*len(raw))
            else:
                return template.T_IGNORED.sample()

        if self._mode == ReadMode.TEXT:
            return template.T_NEWLINE_TEXT.sample()
        return template.T_NEWLINE.sample()

    def _handle_ascii_space_chars(self, raw: bytes) -> SegmentTemplateSample:
        return self._handle_ascii_whitespace_chars(raw)

    def _handle_ascii_printable_chars(self, raw: bytes) -> SegmentTemplateSample:
        return template.T_DEFAULT.sample(raw.decode('utf8', errors='replace'))

    def _verify(self, unmatched: bytes):
        raw_input = self._parser_buffer.get_raw()
        if not raw_input.endswith(unmatched):
            assert len(unmatched) == 0, f'Some bytes unprocessed ({len(unmatched)}: {unmatched.hex(" ")!s:.32s})'

        raw_len = self._chain_buffer.data_len
        processed_len = self._chain_buffer._processed.data_len
        if self._mode == ReadMode.BINARY:
            assert raw_len == processed_len, \
                f'Total count of processed bytes {processed_len} is not equal to count of raw bytes {raw_len}'
