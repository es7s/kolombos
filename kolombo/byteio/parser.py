from __future__ import annotations

import re
from re import Match
from typing import Callable, cast

from pytermor.util import StringFilter, apply_filters

from . import ReadMode
from .segment import template
from .segment.segment import Segment
from kolombo.byteio.sequencer import Sequencer
from ..settings import Settings


class Parser:
    def __init__(self, mode: ReadMode, sequencer: Sequencer):
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
        self._sequencer: Sequencer = sequencer

    def parse(self):
        self._sequencer.reset_match_counters()
        unmatched = apply_filters(self._sequencer.get_raw(), self.F_SEPARATOR)
        try:
            self._verify(unmatched)
        except AssertionError as e:
            raise RuntimeError(f'Parsing inconsistency at 0x{self._sequencer.offset_raw:x}') from e
        self._sequencer.crop_raw(unmatched)

    def _substitute(self, m: Match) -> bytes:
        mgroups = {idx: grp for idx, grp in enumerate(m.groups()) if grp}
        primary_mgroup = min(mgroups.keys())
        span = cast(bytes, m.group(primary_mgroup+1))

        self._handle(primary_mgroup, span)
        return b''

    def _handle(self, mgroup: int, span: bytes):
        _handler_fn = self._find_handler(mgroup)
        if not _handler_fn:
            raise RuntimeError(f'No handler defined for mgroup {mgroup}: {span.hex(" ")}')

        seg = _handler_fn(span)
        self._sequencer.append_segment(seg)

    def _find_handler(self, mgroup: int) -> Callable[[bytes], Segment]|None:
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

    def _handle_utf8_char_bytes(self, span: bytes) -> Segment:
        if Settings.ignore_utf8:
            return template.T_UTF8.ignore(span)
        if not Settings.decode:
            return template.T_UTF8.default(span)
        return template.T_UTF8.default(span, span.decode('utf8', errors='replace'))

    def _handle_binary_data_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError(f'{span!r}')

    def _handle_csi_esq_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

    def _handle_nf_esq_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

    def _handle_fp_esq_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

    def _handle_fe_esq_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

    def _handle_fs_esq_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

    def _handle_ascii_control_chars(self, span: bytes) -> Segment:
        if Settings.ignore_control:
            return template.T_CONTROL.ignore(span)
        return template.T_CONTROL.default(span)

    def _handle_ascii_whitespace_chars(self, span: bytes) -> Segment:
        if Settings.ignore_space:
            return template.T_WHITESPACE.ignore(span)
        return template.T_WHITESPACE.default(span)

    def _handle_ascii_newline_chars(self, span: bytes) -> Segment:
        tpl = template.T_NEWLINE
        if self._mode == ReadMode.TEXT:
            tpl = template.T_NEWLINE_TEXT

        if Settings.ignore_space:
            if self._mode == ReadMode.TEXT:
                return tpl.default(span, '\n'*len(span))
            return tpl.ignore(span)
        return tpl.default(span)

    def _handle_ascii_space_chars(self, span: bytes) -> Segment:
        return self._handle_ascii_whitespace_chars(span)

    def _handle_ascii_printable_chars(self, span: bytes) -> Segment:
        return template.T_DEFAULT.default(span, span.decode('utf8', errors='replace'))

    def _verify(self, unmatched: bytes):
        raw_input = self._sequencer.get_raw()
        if not raw_input.endswith(unmatched):
            assert len(unmatched) == 0, \
                f'Some bytes unprocessed ({len(unmatched)}: {unmatched.hex(" ")!s:.32s})'

        matched_raw = self._sequencer.match_counter_raw
        assert len(raw_input) == self._sequencer.match_counter_raw, \
            f'Total length of segment\'s raw chunks {matched_raw} is not equal to raw input length {len(raw_input)}'

        if self._mode == ReadMode.BINARY:
            matched_processed = self._sequencer.match_counter_processed
            assert len(raw_input) == matched_processed, \
                f'Total length of segment\'s processed chunks {matched_processed} is not equal to raw input length {len(raw_input)}'
