from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Deque, List, Tuple, Callable

from pytermor import fmt, autof, seq
from pytermor.seq import SequenceSGR, EmptySequenceSGR
from pytermor.util import ReplaceSGR

from kolombo.console import ConsoleDebugBuffer
from kolombo.error import SegmentError, WaitRequest
from kolombo.settings import Settings
from kolombo.util import printd


class Chainable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def data_len(self) -> int: raise NotImplementedError

    @property
    @abstractmethod
    def is_newline(self) -> bool: raise NotImplementedError


class Segment(Chainable):
    def __init__(self, template: SegmentTemplate, raw: bytes, processed: str = None):
        self._template = template
        self._raw = raw
        self._processed = processed

    def split(self, num_bytes: int) -> Segment:
        if not self.is_consistent:
            raise SegmentError('Unknown how to split inconsistent segment')

        left = Segment(self._template, self._raw[:num_bytes], self._processed[:num_bytes])

        self._raw = self._raw[num_bytes:]
        self._processed = self._processed[num_bytes:]
        return left

    @property
    def data_len(self) -> int:
        return len(self._raw)

    @property
    def is_newline(self) -> bool:
        return '\n' in self._processed

    @property
    def is_consistent(self) -> bool:
        return len(self._raw) == len(self._processed)

    @property
    def template(self) -> SegmentTemplate:
        return self._template

    @property
    def raw(self) -> bytes:
        return self._raw

    @property
    def processed(self) -> str:
        return self._processed

    def __repr__(self):
        return f'{self.__class__.__name__}[{self._raw.hex(" ")}]->[{self._processed}]'


class SequenceRef(Chainable):
    def __init__(self, ref: SequenceSGR):
        self._ref: SequenceSGR = ref

    @property
    def data_len(self) -> int:
        return 0

    @property
    def is_newline(self) -> bool:
        return False

    @property
    def ref(self) -> SequenceSGR:
        return self._ref

    def __repr__(self):
        return f'{self.__class__.__name__}::{self._ref!r}'


class OneUseSequenceRef(SequenceRef): pass
class StartSequenceRef(SequenceRef): pass
class StopSequenceRef(SequenceRef): pass


class SegmentFormatter:
    def __init__(self, apply_sgr: bool, encode_sgr: bool, format_fn: Callable[[Segment], str]):
        self._apply_sgr = apply_sgr
        self._encode_sgr = encode_sgr
        self._format_fn = format_fn

    @property
    def apply_sgr(self):
        return self._apply_sgr

    @property
    def encode_sgr(self):
        return self._encode_sgr

    def format(self, segment: Segment) -> str:
        return self._format_fn(segment)


class SegmentBuffer:
    def __init__(self):
        self._segment_chain: Deque[Chainable] = Deque[Chainable]()
        self._active_sgrs: List[SequenceSGR] = []
        self._last_detached_data_len = 0

        self._debug_buffer = ConsoleDebugBuffer('chainbuf')

    @property
    def data_len(self) -> int:
        return sum([el.data_len for el in self._segment_chain])

    @property
    def last_detached_data_len(self) -> int:
        return self._last_detached_data_len

    def attach(self, segment: Segment):
        f = autof(segment.template.opening)
        if len(f.opening_seq.params) == 0 or f.opening_seq.params == [0]:
            self._segment_chain.append(segment)
            return

        self._segment_chain.extend([
            StartSequenceRef(f.opening_seq),
            segment,
            StopSequenceRef(f.opening_seq),
            OneUseSequenceRef(f.closing_seq)
        ])

    def detach_bytes(self, req_bytes: int, force: bool, formatters: List[SegmentFormatter, ...]) -> Tuple[str, ...]:
        if self.data_len >= req_bytes or force:
            detached = self._detach(req_bytes)
            if len(detached) == 0:
                self._debug_buffer.write(1, 'Responsing with EOF')
                raise EOFError

            return self._format_multiple(detached, formatters)

        self._debug_buffer.write(1, 'Responsing with WaitRequest')
        raise WaitRequest

    def detach_line(self, force: bool, formatters: List[SegmentFormatter, ...]) -> Tuple[str, ...]:
        avail_bytes = 0
        has_newline = False
        for el in self._segment_chain:
            avail_bytes += el.data_len
            if el.is_newline:
                has_newline = True
                break

        if avail_bytes == 0:
            self._debug_buffer.write(1, 'Responsing with EOF')
            raise EOFError

        if has_newline or force:
            detached = self._detach(avail_bytes)
            return self._format_multiple(detached, formatters)

        self._debug_buffer.write(1, 'Responsing with WaitRequest')
        raise WaitRequest

    def preview(self, max_input_len: int = 5) -> str:
        preview_data = self._preview_collect(max_input_len)
        raw_byte_len, sgr_byte_len, values, has_more = preview_data

        result = ('len ' +
                  fmt.bold(str(raw_byte_len)) +
                  fmt.italic('+' + str(sgr_byte_len)))

        if Settings.debug_buffer_contents:
            values_str = []
            has_more_str = '..' if has_more else ''
            for value in values:
                if isinstance(value, int):
                    values_str.append(f'{value:02x}')
                elif isinstance(value, SequenceRef):
                    values_str.append(fmt.italic(self._preview_sgr(value.ref.print())))
            result += ': ' + fmt.gray('[' + ' '.join(values_str) + has_more_str + ']')

            if Settings.debug_buffer_contents_full:
                result += '; Active SGR buffer state: '
                sgrs_str = ' '.join([self._preview_sgr(sgr.print()) for sgr in self._active_sgrs])
                result += fmt.gray(f'[{sgrs_str}]')

        return result

    def _detach(self, req_bytes: int) -> List[Chainable]:
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')

        if len(self._segment_chain) == 0:
            return []

        output = []
        while len(self._segment_chain) > 0:
            cur_element = self._segment_chain[0]

            if isinstance(cur_element, Segment):
                if req_bytes == 0:
                    break

                if cur_element.data_len <= req_bytes:
                    output.append(cur_element)
                    req_bytes -= cur_element.data_len

                else:
                    cur_element_left = cur_element.split(req_bytes)
                    output.append(cur_element_left)
                    break

            elif isinstance(cur_element, StartSequenceRef):
                output.append(cur_element)
                self._active_sgrs.append(cur_element.ref)

            elif isinstance(cur_element, StopSequenceRef):
                self._active_sgrs.remove(cur_element.ref)

            elif isinstance(cur_element, OneUseSequenceRef):
                output.append(cur_element)

            self._segment_chain.popleft()

        self._debug_buffer.write(2, 'Detached ' + fmt.bold(str(sum([el.data_len for el in output]))) + ' data byte(s)')
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
        return output

    def _format_multiple(self, detached: List[Chainable], formatters: List[SegmentFormatter, ...]) -> Tuple[str, ...]:
        self._last_detached_data_len = sum([el.data_len for el in detached])

        formatted = []
        for formatter in formatters:
            formatted.append(self._format(detached, formatter))
        return tuple(formatted)

    def _format(self, detached: List[Chainable], formatter: SegmentFormatter) -> str:
        output = self._append_sgr_to_output(formatter, self._get_active_sgrs_opening())

        for cur_element in detached:
            if isinstance(cur_element, Segment):
                output += formatter.format(cur_element)

            elif isinstance(cur_element, SequenceRef):  # StartSequenceRef | OneUseSequenceRef
                output += self._append_sgr_to_output(formatter, cur_element.ref.print())

        output += self._append_sgr_to_output(formatter, self._get_active_sgrs_closing())
        return output

    def _append_sgr_to_output(self, formatter: SegmentFormatter, sgr_str: str) -> str:
        if not formatter.apply_sgr:
            return ''
        if formatter.encode_sgr:
            return self._preview_sgr(sgr_str)
        return sgr_str

    def _get_active_sgrs_opening(self) -> str:
        return ''.join(sgr.print() for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing_str for sgr in self._active_sgrs)

    def _preview_sgr(self, sgr_str: str) -> str:
        return ReplaceSGR('[ǝ\\3]').apply(sgr_str)

    def _preview_collect(self, max_input_len: int = 5) -> Tuple[int, int, List[int|SequenceRef], bool]:
        raw_byte_len = 0
        sgr_byte_len = 0
        result: List[int|SequenceRef] = []
        max_input_exceeded = False
        for idx, el in enumerate(self._segment_chain):
            if idx >= max_input_len:
                max_input_exceeded = True

            if isinstance(el, Segment):
                if not max_input_exceeded:
                    result.extend(el.raw)
                raw_byte_len += el.data_len

            elif isinstance(el, SequenceRef):
                sgr_len = len(el.ref.print())
                if not max_input_exceeded:
                    result.append(el)
                sgr_byte_len += sgr_len

            else:
                raise RuntimeError(f'Unknown Chainable element: {el!r}')

        return raw_byte_len, sgr_byte_len, result, max_input_exceeded


class SegmentTemplate:
    def __init__(self, label: str, type_label: str = '*', opening: SequenceSGR = None):
        self._label = label
        self._type_label = type_label
        self._opening: SequenceSGR = self._opt_arg(opening)

    def __repr__(self):
        return '{}["{}", "{}", {!r}]'.format(
            self.__class__.__name__,
            self._label,
            self._type_label,
            self._opening
    )

    def substitute(self, raw: bytes, processed: str = None) -> Segment:
        if processed is None:
            processed = self._label * len(raw)
        return Segment(self, raw, processed)

    @property
    def label(self) -> str:
        return self._label

    @property
    def type_label(self) -> str:
        return self._type_label

    @property
    def opening(self) -> SequenceSGR:
        return self._opening

    def _opt_arg(self, arg: SequenceSGR | None, allow_none: bool = False) -> SequenceSGR | None:
        if isinstance(arg, SequenceSGR):
            return arg
        if allow_none:
            return None
        return EmptySequenceSGR()


class SegmentTemplateWhitespace(SegmentTemplate):
    def __init__(self, label: str, type_label: str = 'S'):
        opening = seq.DIM
        opening_focused = seq.BG_CYAN + seq.BLACK
        super().__init__(label, type_label, opening=(opening_focused if Settings.focus_space else opening))


T_DEFAULT = SegmentTemplate('.', 'P')
T_IGNORED = SegmentTemplate('×', '', seq.GRAY)
T_UTF8 = SegmentTemplate('▯', 'U', (seq.HI_BLUE + seq.INVERSED) if Settings.focus_utf8 else seq.HI_BLUE)  # ǚṳ
T_WHITESPACE = SegmentTemplateWhitespace('␣')
T_NEWLINE = SegmentTemplateWhitespace('↵')
T_NEWLINE_TEXT = SegmentTemplateWhitespace('↵\n')
T_CONTROL = SegmentTemplate('Ɐ', 'C', (seq.RED + seq.INVERSED) if Settings.focus_control else seq.RED)
T_TEMP = SegmentTemplate('▯', '?', seq.HI_YELLOW + seq.BG_RED)

#  marker_tab = MarkerWhitespace('⇥')
# # marker_tab_keep_orig = MarkerWhitespace('⇥\t')
# # marker_space = MarkerWhitespace('␣', '·')
# # marker_newline = MarkerWhitespace('↵')
# # marker_newline_keep_orig = MarkerWhitespace('\n')
# # marker_vert_tab = MarkerWhitespace('⤓')
# # marker_form_feed = MarkerWhitespace('↡')
# # marker_car_return = MarkerWhitespace('⇤')
# #
# # marker_sgr_reset = MarkerSGRReset('ϴ')
# # marker_sgr = MarkerSGR('ǝ')
# # marker_esq_csi = MarkerEscapeSeq('Ͻ', seq.GREEN)
# #
# # fmt_first_chunk_col = autof(build_c256(231) + build_c256(238, bg=True))
# # fmt_nth_row_col = autof(build_c256(231) + build_c256(238, bg=True) + seq.OVERLINED)
