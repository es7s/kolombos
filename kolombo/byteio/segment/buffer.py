from __future__ import annotations

from typing import Deque, List, Tuple

from pytermor import autof, fmt
from pytermor.seq import SequenceSGR
from pytermor.util import ReplaceSGR

from kolombo.byteio.segment.chainable import Chainable
from kolombo.byteio.segment.processor import SegmentProcessor
from kolombo.byteio.segment.segment import Segment
from kolombo.byteio.segment.sequence_ref import StartSequenceRef, StopSequenceRef, OneUseSequenceRef, SequenceRef
from kolombo.console import ConsoleDebugBuffer
from kolombo.error import WaitRequest
from kolombo.settings import SettingsManager
from kolombo.util import printd


# noinspection PyMethodMayBeStatic
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
        f = autof(segment.opening_seq)
        if len(f.opening_seq.params) == 0 or f.opening_seq.params == [0]:
            self._segment_chain.append(segment)
            return

        self._segment_chain.extend([
            StartSequenceRef(f.opening_seq),
            segment,
            StopSequenceRef(f.opening_seq),
            OneUseSequenceRef(f.closing_seq)
        ])

    def detach_bytes(self, req_bytes: int, force: bool, formatters: List[SegmentProcessor, ...]) -> Tuple[str, ...]:
        if self.data_len >= req_bytes or force:
            detached = self._detach(req_bytes)
            if len(detached) == 0:
                self._debug_buffer.write(1, 'Responsing with EOF')
                self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
                raise EOFError

            return self._format_multiple(detached, formatters)

        self._debug_buffer.write(1, 'Responsing with WaitRequest')
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
        raise WaitRequest

    def detach_line(self, force: bool, formatters: List[SegmentProcessor, ...]) -> Tuple[str, ...]:
        avail_bytes = 0
        has_newline = False
        for el in self._segment_chain:
            avail_bytes += el.data_len
            if el.is_newline:
                has_newline = True
                break

        if avail_bytes == 0:
            self._debug_buffer.write(1, 'Responsing with EOF')
            self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
            raise EOFError

        if has_newline or force:
            detached = self._detach(avail_bytes)
            return self._format_multiple(detached, formatters)

        self._debug_buffer.write(1, 'Responsing with WaitRequest')
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
        raise WaitRequest

    def preview(self, max_input_len: int = 5) -> str:
        preview_data = self._preview_collect(max_input_len)
        raw_byte_len, sgr_byte_len, values, has_more = preview_data

        result = ('len ' +
                  fmt.bold(raw_byte_len) +
                  fmt.italic(f'+{sgr_byte_len}'))

        if SettingsManager.app_settings.debug_buffer_contents:
            values_str = []
            has_more_str = '..' if has_more else ''
            for value in values:
                if isinstance(value, int):
                    values_str.append(f'{value:02x}')
                elif isinstance(value, SequenceRef):
                    values_str.append(fmt.italic(self._preview_sgr(value.ref.print())))
            result += ': ' + fmt.gray('[' + ' '.join(values_str) + has_more_str + ']')

            if SettingsManager.app_settings.debug_buffer_contents_full:
                result += '. Active SGR buffer state: '
                sgrs_str = ' '.join([self._preview_sgr(sgr.print()) for sgr in self._active_sgrs])
                result += fmt.gray(f'[{sgrs_str}]')

        return result

    def _detach(self, req_bytes: int) -> List[Chainable]:
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')

        if len(self._segment_chain) == 0:
            return []

        output = []
        output.extend([OneUseSequenceRef(sgr) for sgr in self._active_sgrs])
        while len(self._segment_chain) > 0:
            cur_element = self._segment_chain[0]

            if isinstance(cur_element, Segment):
                if req_bytes == 0:
                    break

                if cur_element.data_len <= req_bytes:
                    output.append(cur_element)
                    req_bytes -= cur_element.data_len
                    self._segment_chain.popleft()
                    continue

                else:
                    cur_element_left = cur_element.split(req_bytes)
                    output.append(cur_element_left)
                    break

            elif isinstance(cur_element, StartSequenceRef):
                if req_bytes == 0:
                    break
                output.append(cur_element)
                self._active_sgrs.append(cur_element.ref)

            elif isinstance(cur_element, StopSequenceRef):
                self._active_sgrs.remove(cur_element.ref)

            elif isinstance(cur_element, OneUseSequenceRef):
                output.append(cur_element)

            self._segment_chain.popleft()

        self._debug_buffer.write(2, 'Detached ' + fmt.bold(sum([el.data_len for el in output])) + ' data byte(s)')
        self._debug_buffer.write(2, f'Buffer state: {printd(self)}')
        output.extend([OneUseSequenceRef(autof(sgr).closing_seq) for sgr in self._active_sgrs])
        return output

    def _format_multiple(self, detached: List[Chainable], formatters: List[SegmentProcessor, ...]) -> Tuple[str, ...]:
        self._last_detached_data_len = sum([el.data_len for el in detached])

        formatted = []
        for formatter in formatters:
            formatted.append(self._format(detached, formatter))
        return tuple(formatted)

    def _format(self, detached: List[Chainable], formatter: SegmentProcessor) -> str:
        output = ''
        for cur_element in detached:
            if isinstance(cur_element, Segment):
                output += formatter.format(cur_element)

            elif isinstance(cur_element, SequenceRef):  # StartSequenceRef | OneUseSequenceRef
                output += self._append_sgr_to_output(formatter, cur_element.ref.print())

        #output += self._append_sgr_to_output(formatter, self._get_active_sgrs_closing())
        return output

    def _append_sgr_to_output(self, formatter: SegmentProcessor, sgr_str: str) -> str:
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

    def _preview_collect(self, max_input_len: int = 5) -> Tuple[int, int, List[int | SequenceRef], bool]:
        raw_byte_len = 0
        sgr_byte_len = 0
        result: List[int | SequenceRef] = []
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
