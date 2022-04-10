from __future__ import annotations

from typing import Deque, AnyStr, Union, List, Callable, Tuple

from pytermor import autof, fmt, seq
from pytermor.seq import SequenceSGR

from kolombo.byteio.segment.template import Segment
from kolombo.console import Console, ConsoleBuffer
from kolombo.error import BufferWait
from kolombo.settings import Settings
from kolombo.util import printd

class Chain:
    def __init__(self):
        self._elements: Deque[Chainable] = Deque[Chainable]()
        self._active_sgrs: List[SequenceSGR] = []

    def detach_flat(self, num_bytes: int, processor_fn: Processor = None) -> Tuple[int, bytes, str]:
        if len(self._elements) == 0:
            return 0, b'', ''

        num_bytes_origin = num_bytes
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
                    output_proc += processor_fn(cur_element)
                    num_bytes -= len(cur_element)
                else:
                    if isinstance(cur_element, bytes):
                        output_raw += cur_element[:num_bytes]
                    output_proc += processor_fn(cur_element[:num_bytes])
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



    def _get_active_sgrs_opening(self) -> str:
        return ''.join(sgr.print() for sgr in self._active_sgrs)

    def _get_active_sgrs_closing(self) -> str:
        return ''.join(autof(sgr).closing_str for sgr in self._active_sgrs)



class ChainBuffer:
    def __init__(self):
        self._raw: Chain = Chain()
        self._processed: Chain = Chain()
        self._debug_buffer = Console.register_buffer(ConsoleBuffer(1, 'chainbuf'))
        self._debug_buffer2 = Console.register_buffer(ConsoleBuffer(2, 'chainbuf'))

