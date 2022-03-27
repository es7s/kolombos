import re
from typing import AnyStr, Union, List, Match

import pytermor
from pytermor import SGRSequence
from pytermor.preset import fmt_green, fmt_cyan
from pytermor.string_filter import ReplaceSGRSequences

from ..formatter import AbstractFormatter
from ..marker.registry import MarkerRegistry
from ..settings import Settings
from ..writer import Writer


class TextFormatter(AbstractFormatter):
    def __init__(self, _writer: Writer):
        super().__init__(_writer)
        self._whitespace_map = {
            0x09: MarkerRegistry.marker_tab.print(),
            0x0b: MarkerRegistry.marker_vert_tab.print(),
            0x0c: MarkerRegistry.marker_form_feed.print(),
            0x0d: MarkerRegistry.marker_car_return.print(),
            0x0a: MarkerRegistry.marker_newline.print() + '\x0a',  # actual newline
            0x20: MarkerRegistry.marker_space.print(),
        }

    def get_fallback_char(self) -> AnyStr:
        return ''

    #  def _postprocess(self, processed_input: str) -> str:
    # if Settings.include_space:
    #    processed_input = re.sub(
    #        r'(\x20+)',
    #        lambda m: MarkerWhitespace.sget_fmt()(m.group(1)),
    #        processed_input
    #    )
    #    processed_input = re.sub(r'\x20', FormatRegistry.marker_space.marker_char, processed_input)
    # return processed_input

    def format(self, raw_input: Union[str, List[str]], offset: int):
        if type(raw_input) is str:
            raw_input = [raw_input]

        for raw_input_line in raw_input:
            processed_input = self._postprocess_input(
                self._process_input(raw_input_line)
            )

            if Settings.no_line_numbers:
                prefix = ''
            else:
                prefix = fmt_green(f'{offset + 1:2d}') + fmt_cyan('│')

            formatted_input = prefix + processed_input
            aligned_raw_input = (pytermor.apply_filters(prefix, ReplaceSGRSequences(''))) + raw_input_line

            self._writer.write_line(formatted_input, aligned_raw_input)
            offset += 1

    def _format_csi_sequence(self, match: Match) -> AnyStr:
        introducer = match.group(1)  # e.g. '['
        params = match.group(2)  # e.g. '1;7'
        terminator = match.group(3)  # e.g. 'm'

        params_splitted = re.split(r'[^0-9]+', params)
        params_values = list(filter(self._filter_sgr_param, params_splitted))

        if Settings.ignore_esc:
            if terminator == SGRSequence.TERMINATOR and not Settings.no_color_content:
                return SGRSequence(*params_values).str
            return ''

        info = ''
        if Settings.effective_info_level() >= 1:
            info += SGRSequence.SEPARATOR.join(params_values)
        if Settings.effective_info_level() >= 2:
            info = introducer + info + terminator

        if terminator == SGRSequence.TERMINATOR:
            if len(params_values) == 0:
                return MarkerRegistry.marker_sgr_reset.print()
            return MarkerRegistry.marker_sgr.print(info, SGRSequence(*params_values))
        else:
            return MarkerRegistry.marker_esc_csi.print(info)
