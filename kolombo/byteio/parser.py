from __future__ import annotations

import re
from re import Match
from typing import cast

from pytermor import seq
from pytermor.util import StringFilter, apply_filters

from . import ParserBuffer
from .segment import SegmentBuffer, Segment
from .template import Template, TemplateRegistry
from ..console import ConsoleDebugBuffer, Console


# noinspection PyMethodMayBeStatic
class Parser:
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer, template_registry: TemplateRegistry):
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

        self._parser_buffer: ParserBuffer = parser_buffer
        self._segment_buffer: SegmentBuffer = segment_buffer
        self._template_registry: TemplateRegistry = template_registry
        self._offset = 0

        self._debug_buffer = ConsoleDebugBuffer('parser', seq.CYAN)

    def parse(self, offset: int):
        raw = self._parser_buffer.get_raw()
        self._offset = offset
        self._debug_buffer.write(1, f'Parsing segment: {Console.printd(raw)}')

        unmatched = apply_filters(raw, self.F_SEPARATOR)
        try:
            assert len(unmatched) == 0, f'Some bytes unprocessed: {Console.printd(unmatched)})'
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
        template = self._find_template(mgroup)
        if not template:
            raise RuntimeError(f'No template defined for mgroup {mgroup}: {raw.hex(" ")}')

        segment = template.substitute(raw)
        self._debug_print_match_segment(mgroup, raw, segment, suboffset)

        self._segment_buffer.attach(segment)

    def _find_template(self, mgroup: int) -> Template|None:
        if mgroup == 0:
            return self._template_registry.UTF_8_SEQ
        if mgroup == 1:
            return self._template_registry.BINARY_DATA
        #if mgroup == 2:
        #    return self._handle_csi_esq_bytes
        if mgroup == 21:
            return self._template_registry.CONTROL_CHAR  # wat
        if mgroup == 22:
            return self._template_registry.WHITESPACE_CARR_RETURN  # wat
        if mgroup == 23:
            return self._template_registry.WHITESPACE_SPACE
        if mgroup == 24:
            return self._template_registry.WHITESPACE_NEWLINE
        if mgroup == 25:
            return self._template_registry.PRINTABLE_CHAR
        return None
    
    def _debug_print_match_segment(self, mgroup: int, raw: bytes, segment: Segment, suboffset: int):
        debug_msg = f'Match group #{mgroup:02d}'
        debug_msg += f'/{segment.type_label}: {Console.printd(raw)}'
        debug_processed_bytes = segment.processed.encode('ascii', errors="replace")
        if raw != debug_processed_bytes:
            debug_msg += f' -> {Console.printd(debug_processed_bytes)}'
        self._debug_buffer.write(2, debug_msg, offset=(self._offset + suboffset))
