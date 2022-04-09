from __future__ import annotations

from typing import Deque, AnyStr, Union, List, Callable, Tuple

from pytermor import autof, fmt, seq
from pytermor.seq import SequenceSGR

from kolombo.byteio.segment.template import SegmentTemplateSample
from kolombo.console import Console, ConsoleBuffer
from kolombo.error import BufferWait
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
        self._cur_element: AnyStr|None = None
        self._active_sgrs: List[SequenceSGR] = []
        self._default_transformer = lambda b: b

    def preview(self, max_input_len: int = 5) -> Tuple[int, int, List[str]]:
        raw_data_byte_len = 0
        raw_sgr_byte_len = 0
        result: List[str] = []
        for idx, el in enumerate(self._elements):
            if isinstance(el, bytes):
                result.extend([f'{b:02x}' for b in el])
                raw_data_byte_len += len(el)
            else:
                result.append(f'{el.ref!r}')
                raw_sgr_byte_len += len(el.ref.print())
        return raw_data_byte_len, raw_sgr_byte_len, result

    def attach(self, *elements: Chainable):
        for element in elements:
            self._elements.append(element)

    def detach_flat(self, num_bytes: int, transform_fn: Transformer = None) -> Tuple[int, bytes, str]:
        num_bytes_origin = num_bytes
        if transform_fn is None:
            transform_fn = self._default_transformer
        if len(self._elements) == 0 and self._cur_element is None:
            raise EOFError

        output_raw = b''
        output_proc = self._get_active_sgrs_opening()
        while (len(self._elements) > 0 or self._cur_element is not None) and num_bytes > 0:
            if self._cur_element is None:
                self._cur_element = self._elements.popleft()

            if isinstance(self._cur_element, (str, bytes)):
                if len(self._cur_element) <= num_bytes:
                    if isinstance(self._cur_element, bytes):
                        output_raw += self._cur_element
                    output_proc += transform_fn(self._cur_element)
                    num_bytes -= len(self._cur_element)
                else:
                    if isinstance(self._cur_element, bytes):
                        output_raw += self._cur_element[:num_bytes]
                    output_proc += transform_fn(self._cur_element[:num_bytes])
                    self._cur_element = self._cur_element[num_bytes:]
                    num_bytes = 0
                    if len(self._cur_element) > 0:
                        continue

            if isinstance(self._cur_element, OneUseSequenceRef):
                output_proc += self._cur_element.ref.print()

            if isinstance(self._cur_element, StartSequenceRef):
                sgr_to_start = self._cur_element.ref
                output_proc += sgr_to_start.print()
                self._active_sgrs.append(self._cur_element.ref)

            if isinstance(self._cur_element, StopSequenceRef):
                self._active_sgrs.remove(self._cur_element.ref)

            self._cur_element = None

        output_proc += self._get_active_sgrs_closing()
        return num_bytes_origin - num_bytes, output_raw, output_proc

    @property
    def data_len(self) -> int:
        return sum([
            el.data_len if isinstance(el, SequenceRef) else len(el)
            for el in self._elements
        ])

    def _get_active_sgrs_opening(self) -> str:
        return ''.join(sgr.print() for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing_str for sgr in self._active_sgrs)


class ChainBuffer:
    def __init__(self):
        self._raw: Chain = Chain()
        self._processed: Chain = Chain()
        self._debug_buffer = Console.register_buffer(ConsoleBuffer(3, 'chainbuf', autof(seq.HI_YELLOW)))

    def add(self, raw: bytes, sample: SegmentTemplateSample):
        fmt = autof(sample.template.opening)
        processed = sample.get_processed(len(raw))

        self._both_attach(StartSequenceRef(fmt.opening_seq))
        self._raw.attach(raw)
        self._processed.attach(processed)
        self._both_attach(StopSequenceRef(fmt.opening_seq), OneUseSequenceRef(fmt.closing_seq))

    def read(self,
             num_bytes: int,
             transformer_raw: TransformerByte = None,
             transformer_processed: TransformerStr = None
             ) -> Tuple[int, bytes, str, str]:
        self.status()
        self._debug_buffer.write(f'Read request, len ' + fmt.bold(f'{num_bytes}'))
        if self.data_len < num_bytes:
            self._debug_buffer.write('Response: BufferWait')
            self.status()
            raise BufferWait('Not enough data to detach')

        try:
            raw_bytes_rcvd, raw_result, proc_hex_result = self._raw.detach_flat(num_bytes, transformer_raw)
            proc_bytes_rcvd, _, proc_str_result = self._processed.detach_flat(num_bytes, transformer_processed)
            assert raw_bytes_rcvd == proc_bytes_rcvd
            return raw_bytes_rcvd, raw_result, proc_hex_result, proc_str_result

        except EOFError:
            self._debug_buffer.write('Response: EOF')
            self.status()
            raise

    def read_all(self,
                 transformer_raw: TransformerByte = None,
                 transformer_processed: TransformerStr = None
                 ) -> Tuple[int, bytes, str, str]:
        return self.read(self.data_len, transformer_raw, transformer_processed)

    def status(self):
        self._debug_buffer.write(f'Raw buffer state: {printd(self._raw)}')

    @property
    def data_len(self) -> int:
        return self._raw.data_len

    def _both_attach(self, *elements: Chainable):
        self._raw.attach(*elements)
        self._processed.attach(*elements)
