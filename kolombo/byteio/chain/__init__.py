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

        result = autof(seq.GRAY)('['+
                                 ' '.join(re.findall('(..)', result)[:max_input_len]) +
                                 ('..')+
                                 ']')

        sgr_total_len = sum([len(str(el.ref)) for el in self._elements if isinstance(el, SequenceRef)])
        raw_byte_total_len = len(self)
        return f'raw {fmt.bold(str(raw_byte_total_len))} + ' \
               f'sgr {fmt.bold(str(sgr_total_len))} ' + \
               result

    def attach(self, *elements: Chainable):
        for element in elements:
            self._elements.append(element)

    def detach_flat(self, num_bytes: int, transform_fn: Transformer = None) -> str:
        if transform_fn is None:
            transform_fn = self._default_transformer
        if len(self._elements) == 0 and self._cur_element is None:
            raise EOFError

        output = self._get_active_sgrs_opening()
        while (len(self._elements) > 0 or self._cur_element is not None) and num_bytes > 0:
            if self._cur_element is None:
                self._cur_element = self._elements.popleft()

            if isinstance(self._cur_element, (str, bytes)):
                if len(self._cur_element) <= num_bytes:
                    output += transform_fn(self._cur_element)
                    num_bytes -= len(self._cur_element)
                else:
                    output += transform_fn(self._cur_element[:num_bytes])
                    self._cur_element = self._cur_element[num_bytes:]
                    num_bytes = 0
                    if len(self._cur_element) > 0:
                        continue

            if isinstance(self._cur_element, OneUseSequenceRef):
                output += str(self._cur_element.ref)

            if isinstance(self._cur_element, StartSequenceRef):
                sgr_to_start = str(self._cur_element.ref)
                output += str(sgr_to_start)
                self._active_sgrs.append(self._cur_element.ref)

            if isinstance(self._cur_element, StopSequenceRef):
                self._active_sgrs.remove(self._cur_element.ref)

            self._cur_element = None

        output += self._get_active_sgrs_closing()
        return output

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
             ) -> Tuple[str, str, str]:
        if len(self._raw) < num_bytes:
            raise BufferWait('Not enough data to detach')
        try:
            raw_result, processed_result = self._raw.detach_flat(num_bytes, transformer_raw), \
                                           self._processed.detach_flat(num_bytes, transformer_processed)
            return ReplaceSGR()(raw_result), raw_result, processed_result
        except EOFError as e:
            raise e

    def read_all(self,
                 transformer_raw: TransformerByte = None,
                 transformer_processed: TransformerStr = None
                 ) -> Tuple[str, str, str]:
        return self.read(len(self._raw), transformer_raw, transformer_processed)

    def status(self):
        self._debug_buf.write(f'Chain raw buffer: {printd(self._raw)}')

    def _both_attach(self, *elements: Chainable):
        self._raw.attach(*elements)
        self._processed.attach(*elements)
