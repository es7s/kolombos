# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

import re
from re import Match
from typing import cast, Dict, Callable, List

from pytermor import seq, apply_filters, StringFilter, fmt

from . import ParserBuffer
from ..segment import SegmentBuffer, Segment
from ..template import Template, TemplateRegistry
from ...console import ConsoleDebugBuffer, Console

MatchResolver = Callable[[Match], Template]


# noinspection PyMethodMayBeStatic
class Parser:
    def __init__(self, parser_buffer: ParserBuffer, segment_buffer: SegmentBuffer, template_registry: TemplateRegistry):
        self._parser_buffer: ParserBuffer = parser_buffer
        self._segment_buffer: SegmentBuffer = segment_buffer
        self._template_registry: TemplateRegistry = template_registry

        self.F_SEPARATOR = StringFilter[bytes](
            lambda b: re.sub(
                b'('                                   # [0] UTF-8
                b'[\xc2-\xdf][\x80-\xbf]|'             # - non-overlong 2-byte
                b'\xe0[\xa0-\xbf][\x80-\xbf]|'         # - excluding overlongs
                b'[\xe1-\xec\xee\xef][\x80-\xbf]{2}|'  # - straight 3-byte
                b'\xed[\x80-\x9f][\x80-\xbf]|'         # - excluding surrogates
                b'\xf0[\x90-\xbf][\x80-\xbf]{2}|'      # - planes 1-3
                b'[\xf1-\xf3][\x80-\xbf]{3}|'          # - planes 4-15        # # # # # # # # # # # # # # # # # # # # #
                b'\xf4[\x80-\x8f][\x80-\xbf]{2}'       # - plane 16           # double slash in grp 4 is essential or #
                b')|'                                                         # regex goes batshit crazy: \x5b is '[' #
                +                                                             # # # # # # # # # # # # # # # # # # # # #
                b'([\x80-\xff]+)|'                     # [1] BINARY DATA                                              |
                +                                                             # ESCAPE SEQUENCES                      |
                b'((\x1b)(\\x5b)([\x30-\x3f]*)([\x20-\x2f]*)([\x40-\x7e]))|'  # [ 2|  3-7] CSI/SGR sequences   <- - - +
                b'((\x1b)([\x20-\x2f])([\x20-\x2f]*)([\x30-\x7e]))|'          # [ 8| 9-12] nF escape sequences
                b'((\x1b)([\x30-\x3f]))|'                                     # [13|14-15] Fp escape sequences
                b'((\x1b)([\x40-\x5f]))|'                                     # [16|17-18] Fe escape sequences
                b'((\x1b)([\x60-\x7e]))|'                                     # [19|20-21] Fs escape sequences
                +                                      # 7-BIT ASCII
                b'([\x01-\x07\x0e-\x1a\x1c-\x1f]+)|'   # [22] generic control chars
                b'(\x00+)|'                            # [23] control chars/nulls
                b'(\x08+)|'                            # [24] control chars/backspaces
                b'(\x1b)|'                             # [25] control chars/escape (one, outside of sequences)
                b'(\x7f+)|'                            # [26] control chars/deletes
                b'(\x09+)|'                            # [27] whitespaces/tabs
                b'(\x0a)|'                             # [28] whitespaces/newline (one)
                b'(\x0b+)|'                            # [29] whitespaces/vertical tabs
                b'(\x0c+)|'                            # [30] whitespaces/form feeds
                b'(\x0d+)|'                            # [31] whitespaces/carriage returns
                b'(\x20+)|'                            # [32] whitespace/spaces
                b'([\x21-\x7e]+)',                     # [33] printable chars (letters, digits, punctuation)
                self._substitute, b
            ))

        self.MGROUP_TO_TPL_MAP: Dict[int, Template|MatchResolver] = {  # @FIXME map templates to regexps
            0: self._template_registry.UTF_8_SEQ,                      #        and build F_SEPARATOR automatically?
            1: self._template_registry.BINARY_DATA,
            2: self._resolve_escape_seq_csi,
            8: self._template_registry.ESCAPE_SEQ_NF,
            13: self._template_registry.ESCAPE_SEQ_FP,
            16: self._template_registry.ESCAPE_SEQ_FE,
            19: self._template_registry.ESCAPE_SEQ_FS,
            22: self._template_registry.CONTROL_CHAR,
            23: self._template_registry.CONTROL_CHAR_NULL,
            24: self._template_registry.CONTROL_CHAR_BACKSPACE,
            25: self._template_registry.CONTROL_CHAR_ESCAPE,
            26: self._template_registry.CONTROL_CHAR_DELETE,
            27: self._template_registry.WHITESPACE_TAB,
            28: self._template_registry.WHITESPACE_NEWLINE,
            29: self._template_registry.WHITESPACE_VERT_TAB,
            30: self._template_registry.WHITESPACE_FORM_FEED,
            31: self._template_registry.WHITESPACE_CARR_RETURN,
            32: self._template_registry.WHITESPACE_SPACE,
            33: self._template_registry.PRINTABLE_CHAR,
        }

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

        self._handle(m, primary_mgroup, raw)
        return b''

    def _handle(self, m: Match, mgroup: int, raw: bytes):
        template = self._resolve_match(m, mgroup)
        segments = template.substitute(raw)
        suboffset = m.start(mgroup + 1)

        self._debug_print_match_segments(mgroup, raw, segments, suboffset)
        self._segment_buffer.attach(*segments)

    def _resolve_match(self, m: Match, mgroup: int) -> Template:
        if mgroup not in self.MGROUP_TO_TPL_MAP.keys():
            raise RuntimeError(f'No template or resolver defined for mgroup {mgroup}: {m.groups()}')

        tpl = self.MGROUP_TO_TPL_MAP[mgroup]
        if isinstance(tpl, Template):
            return tpl
        elif isinstance(tpl, Callable):
            return tpl(m)
        raise TypeError(f'Match must resolve to template or resolver, got {tpl!r}')

    def _resolve_escape_seq_csi(self, m: Match) -> Template:  # @FIXME transform resolver to regexp composite
        is_sgr = (m.group(8) == b'm')
        if is_sgr:
            sgr_params = m.group(6)                             # ↕ overload substitute() for EscapeSequenceSGRTemplate
            if sgr_params == b'' or sgr_params == b'0':         # allow passing in marker details format
                return self._template_registry.ESCAPE_SEQ_SGR_0
            tpl = self._template_registry.ESCAPE_SEQ_SGR
            tpl.set_details_fmt_str(sgr_params)  # @FIXME ugly state, eaugh
            return tpl
        return self._template_registry.ESCAPE_SEQ_CSI

    def _debug_print_match_segments(self, mgroup: int, raw: bytes, segments: List[Segment], suboffset: int):
        debug_msg = f'Match group #{mgroup:02d}: '

        for idx, segment in enumerate(segments):
            cur_raw = raw
            if idx > 0:
                cur_raw = b''
                debug_msg += '; '

            debug_msg += f'Seg {fmt.inversed("<"+segment.type_label+">")}: {Console.printd(cur_raw)}'
            debug_processed_bytes = segment.processed.encode('ascii', errors="replace")
            if cur_raw != debug_processed_bytes:
                debug_msg += f' -> {Console.printd(debug_processed_bytes)}'

        self._debug_buffer.write(2, debug_msg, offset=(self._offset + suboffset))
