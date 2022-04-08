from __future__ import annotations

import re
from builtins import str
from typing import Deque, AnyStr, Union, List, Sized, Callable, Tuple

from pytermor import autof, fmt, seq
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from kolombo.byteio.segment.template import SegmentTemplateSample
from kolombo.console import Console, ConsoleBuffer
from kolombo.util import printd


class SequenceRef(Sized):
    def __init__(self, ref: SequenceSGR):
        self._ref: SequenceSGR = ref

    def __repr__(self):
        return f'{self.__class__.__name__[-3:]}<-{self._ref!r}'

    def __len__(self) -> int:
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


class Chain(Sized):
    def __init__(self):
        self._elements: Deque[Chainable] = Deque[Chainable]()
        self._cur_element: AnyStr|None = None
        self._active_sgrs: List[SequenceSGR] = []
        self._default_transformer = lambda b: b

    def __len__(self) -> int:
        return sum([len(el) for el in self._elements])

    def preview(self, max_input_len: int = 5) -> str:
        result = ''
        for idx, el in enumerate(self._elements):
            if isinstance(el, bytes):
                result += el.hex()
            else:
                result += 'SG'

        result = autof(seq.GRAY)('[' + ' '.join(re.findall('(..)', result)[:max_input_len]) + '.. ]')

        sgr_total_len = sum([len(str(el.ref)) for el in self._elements if isinstance(el, SequenceRef)])
        raw_byte_total_len = len(self)
        return f'len {fmt.bold(str(raw_byte_total_len))} (+{fmt.bold(str(sgr_total_len))} sgr) ' + \
               result

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
                output_proc += str(self._cur_element.ref)

            if isinstance(self._cur_element, StartSequenceRef):
                sgr_to_start = str(self._cur_element.ref)
                output_proc += str(sgr_to_start)
                self._active_sgrs.append(self._cur_element.ref)

            if isinstance(self._cur_element, StopSequenceRef):
                self._active_sgrs.remove(self._cur_element.ref)

            self._cur_element = None

        output_proc += self._get_active_sgrs_closing()
        return num_bytes_origin - num_bytes, output_raw, output_proc

    def _get_active_sgrs_opening(self) -> str:
        return ''.join(str(sgr) for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing for sgr in self._active_sgrs)


class BufferWait(Exception): pass


class ChainBuffer(Sized):
    def __init__(self):
        self._raw: Chain = Chain()
        self._processed: Chain = Chain()
        self._debug_buf = Console.register_buffer(ConsoleBuffer(1, 'chainbuf'))
        self._debug_buf3 = Console.register_buffer(ConsoleBuffer(3, 'chainbuf'))

    def __len__(self):
        return len(self._raw)

    def add(self, raw: bytes, sample: SegmentTemplateSample):
        fmt = autof(sample.template.opening)
        processed = sample.get_processed(len(raw))

        self._both_attach(StartSequenceRef(fmt.opening_seq))
        self._raw.attach(raw)
        self._processed.attach(processed)
        self._both_attach(StopSequenceRef(fmt.opening_seq), OneUseSequenceRef(fmt.closing_seq))

    def read(self, num_bytes: int,
             transformer_raw: TransformerByte = None,
             transformer_processed: TransformerStr = None
             ) -> Tuple[int, bytes, str, str]:
        self._debug_buf3.write(f'Chain read request: len ' + fmt.bold(f'{num_bytes}'), end='', flush=False)
        if len(self._raw) < num_bytes:
            raise BufferWait('Not enough data to detach')
        try:
            raw_bytes_read, raw_result, proc_hex_result = self._raw.detach_flat(num_bytes, transformer_raw)
            _, _, proc_str_result = self._processed.detach_flat(num_bytes, transformer_processed)
            return raw_bytes_read, raw_result, proc_hex_result, proc_str_result
        except EOFError as e:
            raise e

    def read_all(self,
                 transformer_raw: TransformerByte = None,
                 transformer_processed: TransformerStr = None
                 ) -> Tuple[int, bytes, str, str]:
        return self.read(len(self._raw), transformer_raw, transformer_processed)

    def status(self):
        self._debug_buf.write(f'Chain raw buffer: {printd(self._raw)}')

    def _both_attach(self, *elements: Chainable):
        self._raw.attach(*elements)
        self._processed.attach(*elements)
