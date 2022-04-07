import re
from typing import Match

from pytermor import fmt
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from kolombo.byteio.parser_buf import ParserBuffer
from .. import print_offset
from ..chain import ChainBuffer
from ..formatter import AbstractFormatter
from ...settings import Settings


class TextFormatter(AbstractFormatter):
    def __init__(self, parser_buffer: ParserBuffer, data_flow: ChainBuffer):
        super().__init__(parser_buffer, data_flow)

        self._line_num = 0
        # self._whitespace_map = {
        #     '\t':   MarkerRegistry.marker_tab_keep_orig,
        #     '\v':   MarkerRegistry.marker_vert_tab,
        #     '\f':   MarkerRegistry.marker_form_feed,
        #     '\r':   MarkerRegistry.marker_car_return,
        #     '\n':   MarkerRegistry.marker_newline_keep_orig,
        #     '\x20': MarkerRegistry.marker_space,
        # }

    def format(self, offset: int):
        buffer_raw: bytes = b''
        buffer_processed: str = ''

        while seg := self._sequencer.get_active_segment():
            if not seg:
                continue
            raw, processed = seg.read_all(close=True)
            buffer_raw = raw
            #print('A', end='')
            buffer_processed += processed

        for processed in buffer_processed.splitlines(keepends=False):
            self._line_num += 1
            prefix = ''
            if not Settings.no_line_numbers:
                prefix = fmt.green(f'{self._line_num:2d}') + fmt.cyan(f'│  ')

            final = f'{prefix}{processed}\n'
            #final_orig = ReplaceSGR('')(prefix).encode() + buffer_raw

            self._sequencer.append_final(final)
            #self._sequencer.append_final_orig(final_orig)


    def _format_csi_sequence(self, match: Match) -> str:
        if Settings.ignore_esc:
            return ''

        introducer = match.group(1)  # e.g. '['
        params = match.group(2)  # e.g. '1;7'
        terminator = match.group(3)  # e.g. 'm'

        params_splitted = re.split(r'[^0-9]+', params)
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        # option to apply SGRs even with -E
        #if Settings.ignore_esc:
        #    if terminator == SequenceSGR.TERMINATOR and not Settings.no_color_content:
        #        return self._escape_escape_character(str(SequenceSGR(*params_values)))
        #    return ''

        info = ''
        if Settings.effective_info_level() >= 1:
            info += SequenceSGR.SEPARATOR.join(params_values)
        if Settings.effective_info_level() >= 2:
            info = introducer + info + terminator

        if terminator == SequenceSGR.TERMINATOR:
            if len(params_values) == 0:
                result = MarkerRegistry.marker_sgr_reset._print()
            else:
                result = MarkerRegistry.marker_sgr._print(info, SequenceSGR(*params_values))
        else:
            result = MarkerRegistry.marker_esq_csi._print(info)
        return self._escape_escape_character(result)

    def _format_generic_escape_sequence(self, match: Match) -> str:
        if Settings.ignore_esc:
            return self.get_fallback_char()

        introducer = match.group(1)
        info = ''
        if Settings.effective_info_level() >= 1:
            info = introducer
        if Settings.effective_info_level() >= 2:
            info = match.group(0)
        if introducer == ' ':
            introducer = MarkerRegistry.marker_space.marker_char
        charcode = ord(introducer)
        marker = MarkerRegistry.get_esq_marker(charcode)
        return self._escape_escape_character(marker._print() + info)

    def _format_control_char(self, match: Match) -> str:
        if Settings.ignore_control:
            return self.get_fallback_char()

        charcode = ord(match.group(1))
        marker = self._control_char_map.require_or_die(charcode)
        return marker._print()

    def _format_space(self, match: Match) -> str:
        if Settings.ignore_space:
            return MarkerRegistry.marker_ignored.get_fmt()(
                MarkerRegistry.marker_ignored.marker_char * len(match.group(0))
            )

        return MarkerRegistry.marker_space.get_fmt()(
            MarkerRegistry.marker_space.marker_char * len(match.group(0))
        )

    def _format_whitespace(self, match: Match) -> str:
        if Settings.ignore_space:
            if match.group(1) == '\n':
                return f'\n'
            return MarkerRegistry.marker_ignored._print()

        marker = self._whitespace_map.get(match.group(1))
        return marker._print()
