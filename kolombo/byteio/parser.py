from __future__ import annotations

import re
from re import Match
from typing import Callable, List, cast

from pytermor.util import StringFilter, apply_filters

from . import print_offset_debug, ReadMode, align_offset
from .segment import template
from .segment.segment import Segment
from ..settings import Settings


class Parser:
    def __init__(self, mode: ReadMode):
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
                self._create_segment, b
            ))

        self._mode = mode
        self._offset: int = 0
        self._segments: List[Segment] = list()

    def parse(self, raw_input: bytes, offset: int) -> List[Segment]:
        self._offset = offset
        self._segments.clear()

        unmatched = apply_filters(raw_input, self.F_SEPARATOR)
        try:
            self._verify(unmatched, len(raw_input))
        except AssertionError as e:
            raise RuntimeError(f'Parsing inconsistency at {align_offset(offset)}') from e
        return self._segments

    def _create_segment(self, m: Match) -> bytes:
        mgroups = {idx: grp for idx, grp in enumerate(m.groups()) if grp}
        primary_mgroup = min(mgroups.keys())
        span = cast(bytes, m.group(primary_mgroup+1))

        seg = self._handle(primary_mgroup, span)
        print(print_offset_debug(seg.type_label, self._offset + m.start(primary_mgroup + 1), span.hex(" ")), end='')
        return b''

    def _handle(self, mgroup: int, span: bytes):
        _handler_fn = self._find_handler(mgroup)
        if not _handler_fn:
            raise RuntimeError(f'No handler defined for mgroup {mgroup}: {span.hex(" ")}')

        seg = _handler_fn(span)
        self._segments.append(seg)
        return seg

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
            return template.T_IGNORED(span, type_label=template.T_UTF8.type_label.lower())
        if not Settings.decode:
            return template.T_UTF8(span)
        return template.T_UTF8(span, span.decode(errors='replace'))

    def _handle_binary_data_bytes(self, span: bytes) -> Segment:
        raise NotImplementedError

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
        return template.T_CONTROL(span)

    def _handle_ascii_whitespace_chars(self, span: bytes) -> Segment:
        if Settings.ignore_space:
            return template.T_IGNORED(span, type_label=template.T_WHITESPACE.type_label.lower())
        return template.T_WHITESPACE(span, focused=Settings.focus_space)

    def _handle_ascii_newline_chars(self, span: bytes) -> Segment:
        if self._mode == ReadMode.TEXT:
            return template.T_NEWLINE(span, '\n' * len(span), focused=Settings.focus_space)
        if Settings.ignore_space:
            return template.T_IGNORED(span, type_label=template.T_NEWLINE.type_label.lower())
        return template.T_NEWLINE(span, focused=Settings.focus_space)

    def _handle_ascii_space_chars(self, span: bytes) -> Segment:
        return self._handle_ascii_whitespace_chars(span)

    def _handle_ascii_printable_chars(self, span: bytes) -> Segment:
        return template.T_DEFAULT(span, span.decode(errors='replace'))

    def _verify(self, unmatched: bytes, raw_input: int):
        matched_raw = 0
        matched_processed = 0
        for seg in self._segments:
            matched_raw += len(seg.raw)
            matched_processed += len(seg.processed)

        assert len(unmatched) == 0, \
            f'Some bytes unprocessed ({len(unmatched)}: {unmatched!s:.32s})'
        assert raw_input == matched_raw, \
            f'Total length of segment\'s raw chunks {matched_raw} is not equal to raw input length {raw_input}'
