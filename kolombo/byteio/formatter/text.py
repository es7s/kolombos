import re
from typing import List, Match

from pytermor import fmt, seq, autof
from pytermor.seq import SequenceSGR, EmptySequenceSGR
from pytermor.util import ReplaceSGR

from .. import print_offset
from ..formatter import AbstractFormatter
from ..segment.segment import Segment
from ...settings import Settings


class TextFormatter(AbstractFormatter):
    def __init__(self):
        self._line_num = 0
        # self._whitespace_map = {
        #     '\t':   MarkerRegistry.marker_tab_keep_orig,
        #     '\v':   MarkerRegistry.marker_vert_tab,
        #     '\f':   MarkerRegistry.marker_form_feed,
        #     '\r':   MarkerRegistry.marker_car_return,
        #     '\n':   MarkerRegistry.marker_newline_keep_orig,
        #     '\x20': MarkerRegistry.marker_space,
        # }

    def format(self, segs: List[Segment], offset: int):
        e = EmptySequenceSGR()
        assert isinstance(e, EmptySequenceSGR)

        processed_lines = ''.join([autof(s.opening)(s.processed) for s in segs])
        output = []
        output_pipe = []

        for processed_line in processed_lines.splitlines(keepends=True):
            if Settings.no_line_numbers:
                prefix = ''
            else:
                prefix = print_offset(self._line_num, fmt.green)

            formatted_line = prefix + processed_line + str(seq.RESET)
            output.append(formatted_line)
            if Settings.pipe_stderr:
                aligned_raw_line = ReplaceSGR('')(prefix) + processed_line
                output_pipe.append(aligned_raw_line)

            self._line_num += 1

        return ''.join(output), ''.join(output_pipe)

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
                result = MarkerRegistry.marker_sgr_reset.print()
            else:
                result = MarkerRegistry.marker_sgr.print(info, SequenceSGR(*params_values))
        else:
            result = MarkerRegistry.marker_esq_csi.print(info)
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
        return self._escape_escape_character(marker.print() + info)

    def _format_control_char(self, match: Match) -> str:
        if Settings.ignore_control:
            return self.get_fallback_char()

        charcode = ord(match.group(1))
        marker = self._control_char_map.require_or_die(charcode)
        return marker.print()

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
            return MarkerRegistry.marker_ignored.print()

        marker = self._whitespace_map.get(match.group(1))
        return marker.print()
