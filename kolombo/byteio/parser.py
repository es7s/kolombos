from __future__ import annotations

import re
from re import Match
from typing import Callable, cast

from pytermor import seq
from pytermor.util import StringFilter, apply_filters

import kolombo.byteio.segment.template
from kolombo.byteio.parser_buf import ParserBuffer
from . import ReadMode
from .segment.buffer import SegmentBuffer
from .segment.segment import Segment
from ..console import ConsoleDebugBuffer
from ..settings import SettingsManager
from ..util import printd


# noinspection PyMethodMayBeStatic
class Parser:
    def __init__(self, mode: ReadMode, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer):
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
                b'([\x09\x0b-\x0d]+)|(\x20+)|(\x0a)|'   # - whitespaces (\t,\v,\f,\r) | spaces | newline
                b'([\x21-\x7e]+)',                      # - printable chars (letters, digits, punctuation)
                self._substitute, b
            ))

        self._mode = mode
        self._parser_buffer: ParserBuffer = parser_buffer
        self._segment_buffer: SegmentBuffer = segment_buffer
        self._offset = 0

        self._debug_buffer = ConsoleDebugBuffer('parser', seq.CYAN)

    def parse(self, offset: int):
        raw = self._parser_buffer.get_raw()
        self._offset = offset
        self._debug_buffer.write(1, f'Parsing segment: {printd(raw)}')

        unmatched = apply_filters(raw, self.F_SEPARATOR)
        try:
            assert len(unmatched) == 0, f'Some bytes unprocessed: {printd(unmatched)})'
        except AssertionError as e:
            raise RuntimeError(f'Parsing inconsistency at 0x{self._offset:x}/{self._offset:d}') from e

        self._parser_buffer.crop_raw(unmatched)

    def _substitute(self, m: Match) -> bytes:
        mgroups = {idx: grp for idx, grp in enumerate(m.groups()) if grp}
        primary_mgroup = min(mgroups.keys())
        raw = cast(bytes, m.group(primary_mgroup+1))

        self._handle(primary_mgroup, raw, m.start(primary_mgroup + 1))
        return b''

    def _handle(self, mgroup: int, raw: bytes, suboffset: int):
        _handler_fn = self._find_handler(mgroup)
        if not _handler_fn:
            raise RuntimeError(f'No handler defined for mgroup {mgroup}: {raw.hex(" ")}')

        segment = _handler_fn(raw)
        self._debug_print_match_segment(mgroup, raw, segment, suboffset)

        self._segment_buffer.attach(segment)

    def _find_handler(self, mgroup: int) -> Callable[[bytes], Segment] | None:
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
            return self._handle_ascii_space_chars
        if mgroup == 24:
            return self._handle_ascii_newline_char
        if mgroup == 25:
            return self._handle_ascii_printable_chars
        return None
    
    def _debug_print_match_segment(self, mgroup: int, raw: bytes, segment: Segment, suboffset: int):
        debug_msg = f'Match group #{mgroup:02d}'
        debug_msg += f'/{segment.type_label}: {printd(raw)}'
        debug_processed_bytes = segment.processed.encode('ascii', errors="replace")
        if raw != debug_processed_bytes:
            debug_msg += f' -> {printd(debug_processed_bytes)}'
        self._debug_buffer.write(2, debug_msg, offset=(self._offset + suboffset))

    def _handle_utf8_char_bytes(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_utf8:
            return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)

        if self._mode == ReadMode.TEXT or SettingsManager.app_settings.decode:
            decoded = raw.decode('utf8', errors='replace')
            if self._mode == ReadMode.BINARY:
                if len(decoded) < len(raw):
                    decoded = decoded.rjust(len(raw), '_')
                elif len(decoded) > len(raw):
                    decoded = decoded[:len(raw)]
            return kolombo.byteio.segment.template.T_UTF8.substitute(raw, decoded)

        return kolombo.byteio.segment.template.T_UTF8.substitute(raw)

    def _handle_binary_data_bytes(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_binary:
            return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)
        return kolombo.byteio.segment.template.T_BINARY.substitute(raw)

    def _handle_csi_esq_bytes(self, raw: bytes) -> Segment:
        return kolombo.byteio.segment.template.T_TEMP.substitute(raw)

    def _handle_nf_esq_bytes(self, raw: bytes) -> Segment:
        return kolombo.byteio.segment.template.T_TEMP.substitute(raw)

    def _handle_fp_esq_bytes(self, raw: bytes) -> Segment:
        return kolombo.byteio.segment.template.T_TEMP.substitute(raw)

    def _handle_fe_esq_bytes(self, raw: bytes) -> Segment:
        return kolombo.byteio.segment.template.T_TEMP.substitute(raw)

    def _handle_fs_esq_bytes(self, raw: bytes) -> Segment:
        return kolombo.byteio.segment.template.T_TEMP.substitute(raw)

    def _handle_ascii_control_chars(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_control:
            return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)
        return kolombo.byteio.segment.template.T_CONTROL.substitute(raw)

    def _handle_ascii_whitespace_chars(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_space:
            return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)
        return kolombo.byteio.segment.template.T_WHITESPACE.substitute(raw)

    def _handle_ascii_space_chars(self, raw: bytes) -> Segment:
        return self._handle_ascii_whitespace_chars(raw)

    def _handle_ascii_newline_char(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_space:
            if self._mode == ReadMode.TEXT:
                return kolombo.byteio.segment.template.T_NEWLINE_TEXT.substitute(raw, '\n' * len(raw))
            else:
                return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)

        if self._mode == ReadMode.TEXT:
            return kolombo.byteio.segment.template.T_NEWLINE_TEXT.substitute(raw)
        return kolombo.byteio.segment.template.T_NEWLINE.substitute(raw)

    def _handle_ascii_printable_chars(self, raw: bytes) -> Segment:
        if SettingsManager.app_settings.ignore_printable:
            return kolombo.byteio.segment.template.T_IGNORED.substitute(raw)
        return kolombo.byteio.segment.template.T_PRINTABLE.substitute(raw, raw.decode('utf8', errors='replace'))
