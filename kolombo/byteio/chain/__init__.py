from __future__ import annotations

from typing import Deque, AnyStr, Union, List, Callable, Tuple

from pytermor import autof, fmt, seq
from pytermor.seq import SequenceSGR

from kolombo.byteio.segment.template import SegmentTemplateSample
from kolombo.console import Console, ConsoleBuffer
from kolombo.error import BufferWait
from kolombo.settings import Settings
from kolombo.util import printd


class SequenceRef:
    def __init__(self, ref: SequenceSGR):
        self._ref: SequenceSGR = ref

    def __repr__(self):
        return f'{self.__class__.__name__[-3:]}<-{self._ref!r}'

    @property
    def data_len(self) -> int:
        return 0

    @property
    def ref(self) -> SequenceSGR: return self._ref


class OneUseSequenceRef(SequenceRef): pass
class StartSequenceRef(SequenceRef): pass
class StopSequenceRef(SequenceRef): pass


Chainable = Union[AnyStr, SequenceRef]
Transformer = Callable[[AnyStr], str]
TransformerByte = Callable[[bytes], str]
TransformerStr = Callable[[str], str]


class Chain:
    def __init__(self):
        self._elements: Deque[Chainable] = Deque[Chainable]()
        self._active_sgrs: List[SequenceSGR] = []

    def attach(self, *elements: Chainable):
        for element in elements:
            self._elements.append(element)

    def detach_flat(self, num_bytes: int, transform_fn: Transformer = None) -> Tuple[int, bytes, str]:
        num_bytes_origin = num_bytes
        if len(self._elements) == 0:
            raise EOFError

        output_raw = b''
        output_proc = self._get_active_sgrs_opening()
        while len(self._elements) > 0:
            cur_element = self._elements[0]

            if isinstance(cur_element, (str, bytes)):
                if num_bytes == 0:
                    break

                if len(cur_element) <= num_bytes:
                    if isinstance(cur_element, bytes):
                        output_raw += cur_element
                    output_proc += transform_fn(cur_element)
                    num_bytes -= len(cur_element)
                else:
                    if isinstance(cur_element, bytes):
                        output_raw += cur_element[:num_bytes]
                    output_proc += transform_fn(cur_element[:num_bytes])
                    self._elements[0] = cur_element[num_bytes:]
                    num_bytes = 0
                    if len(cur_element) > 0:
                        continue

            if isinstance(cur_element, OneUseSequenceRef):
                output_proc += cur_element.ref.print()

            if isinstance(cur_element, StartSequenceRef):
                sgr_to_start = cur_element.ref
                output_proc += sgr_to_start.print()
                self._active_sgrs.append(cur_element.ref)

            if isinstance(cur_element, StopSequenceRef):
                self._active_sgrs.remove(cur_element.ref)

            self._elements.popleft()

        output_proc += self._get_active_sgrs_closing()
        return num_bytes_origin - num_bytes, output_raw, output_proc

    @property
    def data_len(self) -> int:
        return sum([
            el.data_len if isinstance(el, SequenceRef) else len(el)
            for el in self._elements
        ])

    def preview(self, max_input_len: int = 5) -> str:
        preview_data = self._preview_collect(max_input_len)
        data_byte_len, sgr_byte_len, values, has_more = preview_data

        values_str = []
        has_more_str = '..' if has_more else ''
        for value in values:
            if isinstance(value, int):
                values_str.append(f'{value:02x}')
            else:
                values_str.append(fmt.italic(f'{len(value.ref.print())}xSGR'))

        result = ('len ' +
                  fmt.bold(str(data_byte_len)) +
                  fmt.italic('+' + str(sgr_byte_len)))
        if Settings.debug_buffer_contents:
            result += ': ' + autof(seq.GRAY)('[' + ' '.join(values_str) + has_more_str + ']')
        return result

    def _get_active_sgrs_opening(self) -> str:
        return ''.join(sgr.print() for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing_str for sgr in self._active_sgrs)

    def _preview_collect(self, max_input_len: int = 5) -> Tuple[int, int, List[Chainable], bool]:
        raw_data_byte_len = 0
        raw_sgr_byte_len = 0
        result: List[Chainable] = []
        max_input_exceeded = False
        for idx, el in enumerate(self._elements):
            if idx >= max_input_len:
                max_input_exceeded = True

            if isinstance(el, bytes):
                if not max_input_exceeded:
                    result.extend(el)
                raw_data_byte_len += len(el)
            else:
                sgr_len = len(el.ref.print())
                if not max_input_exceeded:
                    result.append(el)
                raw_sgr_byte_len += sgr_len
        return raw_data_byte_len, raw_sgr_byte_len, result, max_input_exceeded


class ChainBuffer:
    def __init__(self):
        self._raw: Chain = Chain()
        self._processed: Chain = Chain()
        self._debug_buffer = Console.register_buffer(ConsoleBuffer(1, 'chainbuf'))
        self._debug_buffer2 = Console.register_buffer(ConsoleBuffer(2, 'chainbuf'))

    def add(self, raw: bytes, sample: SegmentTemplateSample):
        fmt = autof(sample.template.opening)
        processed = sample.get_processed(len(raw))

        self._both_attach(StartSequenceRef(fmt.opening_seq))
        self._raw.attach(raw)
        self._processed.attach(processed)
        self._both_attach(StopSequenceRef(fmt.opening_seq), OneUseSequenceRef(fmt.closing_seq))

    def read(self,
             num_bytes: int,
             no_wait: bool,
             transformer_raw: TransformerByte = None,
             transformer_processed: TransformerStr = None
             ) -> Tuple[int, bytes, str, str]:
        self._debug_buffer2.write(f'Buffer state: {printd(self._raw)}')
        if self.data_len < num_bytes and not no_wait:
            self._debug_buffer.write('Responsing with BufferWait')
            raise BufferWait('Not enough data to detach')

        try:
            raw_bytes_rcvd, raw_result, proc_hex_result = self._raw.detach_flat(num_bytes, transformer_raw)
            proc_bytes_rcvd, _, proc_str_result = self._processed.detach_flat(num_bytes, transformer_processed)
            self._debug_buffer2.write('Dequeued ' + fmt.bold(str(raw_bytes_rcvd)) + ' byte(s)')
            self._debug_buffer2.write(f'Buffer state: {printd(self._raw)}')
            return raw_bytes_rcvd, raw_result, proc_hex_result, proc_str_result

        except EOFError:
            self._debug_buffer.write('Recieved EOF')
            self._debug_buffer2.write(f'Buffer state: {printd(self._raw)}')
            raise

    @property
    def data_len(self) -> int:
        return self._raw.data_len

    def _both_attach(self, *elements: Chainable):
        self._raw.attach(*elements)
        self._processed.attach(*elements)
