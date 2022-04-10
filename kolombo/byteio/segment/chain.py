from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Deque, List, Callable, Tuple, AnyStr

from pytermor import fmt, autof
from pytermor.seq import SequenceSGR

from kolombo.byteio.segment.template import SegmentTemplate
from kolombo.console import Console, ConsoleBuffer
from kolombo.error import BufferWait, SegmentError
from kolombo.settings import Settings
from kolombo.util import printd


class Chainable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def raw_len(self) -> int: raise NotImplementedError

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
    def raw_len(self) -> int:
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


class SequenceRef(Chainable):
    def __init__(self, ref: SequenceSGR):
        self._ref: SequenceSGR = ref

    def __repr__(self):
        return f'{self.__class__.__name__[-3:]}<-{self._ref!r}'

    @property
    def raw_len(self) -> int:
        return 0

    @property
    def is_newline(self) -> bool:
        return False

    @property
    def ref(self) -> SequenceSGR:
        return self._ref


class OneUseSequenceRef(SequenceRef): pass
class StartSequenceRef(SequenceRef): pass
class StopSequenceRef(SequenceRef): pass


class AbstractChainFormatter(metaclass=ABCMeta):
    def __init__(self, apply_sgr: bool):
        self._apply_sgr = apply_sgr

    @property
    def apply_sgr(self):
        return self._apply_sgr

    @abstractmethod
    def format(self, segment: Segment) -> str: raise NotImplementedError


class ChainBuffer:
    def __init__(self):
        self._elements: Deque[Chainable] = Deque[Chainable]()
        self._active_sgrs: List[SequenceSGR] = []

        self._debug_buffer = Console.register_buffer(ConsoleBuffer(1, 'chainbuf'))
        self._debug_buffer2 = Console.register_buffer(ConsoleBuffer(2, 'chainbuf'))

    @property
    def raw_len(self) -> int:
        return sum([el.raw_len for el in self._elements])

    def attach(self, segment: Segment):
        f = autof(segment.template.opening)

        self._elements.extend([
            StartSequenceRef(f.opening_seq),
            segment,
            StopSequenceRef(f.opening_seq),
            OneUseSequenceRef(f.closing_seq)
        ])

    def detach_bytes(self, req_bytes: int, formatters: Tuple[AbstractChainFormatter, ...]) -> Tuple[str, ...]:
        chain = self._detach(req_bytes)
        if len(chain) == 0:
            raise EOFError

        for formatter in formatters:
            pass


    def detach_line(self, formatters: Tuple[AbstractChainFormatter, ...]) -> Tuple[str, ...]:
        req_bytes = 0
        for el in self._elements:
            req_bytes += el.raw_len
            if el.is_newline:
                break
        if req_bytes == 0:
            raise EOFError

        chain = self._detach(req_bytes)

    def preview(self, max_input_len: int = 5) -> str:
        preview_data = self._preview_collect(max_input_len)
        raw_byte_len, sgr_byte_len, values, has_more = preview_data

        values_str = []
        has_more_str = '..' if has_more else ''
        for value in values:
            if isinstance(value, int):
                values_str.append(f'{value:02x}')
            elif isinstance(value, SequenceRef):
                values_str.append(fmt.italic(f'{len(value.ref.print())}xSGR'))

        result = ('len ' +
                  fmt.bold(str(raw_byte_len)) +
                  fmt.italic('+' + str(sgr_byte_len)))

        if Settings.debug_buffer_contents:
            result += ': ' + fmt.gray('[' + ' '.join(values_str) + has_more_str + ']')

        return result

    def _detach(self, req_bytes: int) -> List[Chainable]:
        if len(self._elements) == 0:
            return []

        output = []
        while len(self._elements) > 0:
            cur_element = self._elements[0]

            if isinstance(cur_element, Segment):
                if req_bytes == 0:
                    break

                if cur_element.raw_len <= req_bytes:
                    output.append(cur_element)
                    req_bytes -= cur_element.raw_len

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

            self._elements.popleft()

        return output

    def _format(self, detached: List[Chainable], formatter: AbstractChainFormatter) -> str:
        output = ''
        if formatter.apply_sgr:
            output += self._get_active_sgrs_opening()

        for cur_element in detached:
            if isinstance(cur_element, Segment):
                output += formatter.format(cur_element)

            elif isinstance(cur_element, SequenceRef):  # StartSequenceRef | OneUseSequenceRef
                if formatter.apply_sgr:
                    output += cur_element.ref.print()

        if formatter.apply_sgr:
            output += self._get_active_sgrs_closing()

        return output

    def _get_active_sgrs_opening(self) -> str:
        return ''.join(sgr.print() for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing_str for sgr in self._active_sgrs)

    def _preview_collect(self, max_input_len: int = 5) -> Tuple[int, int, List[int|SequenceRef], bool]:
        raw_byte_len = 0
        sgr_byte_len = 0
        result: List[int|SequenceRef] = []
        max_input_exceeded = False
        for idx, el in enumerate(self._elements):
            if idx >= max_input_len:
                max_input_exceeded = True

            if isinstance(el, Segment):
                if not max_input_exceeded:
                    result.extend(el.raw)
                raw_byte_len += el.raw_len

            elif isinstance(el, SequenceRef):
                sgr_len = len(el.ref.print())
                if not max_input_exceeded:
                    result.append(el)
                sgr_byte_len += sgr_len

            else:
                raise RuntimeError(f'Unknown Chainable element: {el!r}')

        return raw_byte_len, sgr_byte_len, result, max_input_exceeded
