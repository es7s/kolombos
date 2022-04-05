from typing import AnyStr, Deque

from . import AbstractModeProcessor
from ..app import App
from ..byteio import ReadMode
from ..byteio.formatter import FormatterFactory
from ..byteio.parser import Parser
from ..byteio.reader import Reader
from ..byteio.segment.segment import Segment
from ..byteio.writer import Writer
from ..settings import Settings


class ByteIoProcessor(AbstractModeProcessor):
    def _init(self, read_mode: ReadMode):
        self._reader = Reader(Settings.filename, self._process_chunk_buffered)
        self._parser = Parser(read_mode)
        self._formatter = FormatterFactory.create(read_mode)
        self._writer = Writer()

        self._segment_queue: Deque[Segment] = Deque[Segment]()

    def invoke(self):
        try:
            self._init(self._get_read_mode_from_settings())
            self._reader.read()

        except UnicodeDecodeError:
            self._reader.close()
            self._switch_mode_or_exit()

            self._init(ReadMode.BINARY)
            self._reader.read()

    def _process_chunk_buffered(self, raw_input: bytes, offset: int):
        segs = self._parser.parse(raw_input, offset)

        self._segment_queue.extend(segs)
        output = self._formatter.format([s for s in self._segment_queue], offset)
        self._segment_queue.clear()

        self._writer.write_line(*output)

    def _get_read_mode_from_settings(self) -> ReadMode:
        if Settings.binary:
            return ReadMode.BINARY
        elif Settings.text:
            return ReadMode.TEXT
        # auto:
        return ReadMode.TEXT

    def _switch_mode_or_exit(self):
        print('Binary data detected, cannot proceed in text mode')

        if not Settings.auto:
            print('Use -b option to run in binary mode')
            App.exit(2)

        if self._reader.reading_stdin:
            print('Cannot repeat input stream reading because it\'s stdin')
            App.exit(3)
