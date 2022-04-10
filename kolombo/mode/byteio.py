from ..byteio.parser_buf import ParserBuffer
from . import AbstractModeProcessor
from ..app import App
from ..byteio import ReadMode
from ..byteio.formatter import FormatterFactory
from ..byteio.parser import Parser
from ..byteio.reader import Reader
from ..byteio.segment.chain import SegmentBuffer
from ..console import Console, ConsoleDebugBuffer
from ..settings import Settings


class ByteIoProcessor(AbstractModeProcessor):
    def _init(self, read_mode: ReadMode):
        self._parser_buffer = ParserBuffer()
        self._segment_buffer = SegmentBuffer()

        self._reader = Reader(Settings.filename, self._process_chunk_buffered)
        self._parser = Parser(read_mode, self._parser_buffer, self._segment_buffer)
        self._formatter = FormatterFactory.create(read_mode, self._parser_buffer, self._segment_buffer)

    def invoke(self):
        #try:
        self._init(self._get_read_mode_from_settings())
        self._reader.read()

        #except BinaryDataError:
        #    self._reader.close()
        #    self._switch_mode_or_exit()

        #    self._init(ReadMode.BINARY)
        #    self._reader.read()

    def _process_chunk_buffered(self, raw_input: bytes, offset: int, finish: bool):
        self._parser_buffer.append_raw(raw_input, finish)
        self._parser.parse(offset)
        self._formatter.format()

        ConsoleDebugBuffer().write(1, Console.get_separator_line())

    def _get_read_mode_from_settings(self) -> ReadMode:
        if Settings.binary:
            return ReadMode.BINARY
        elif Settings.text:
            return ReadMode.TEXT
        # auto:
        return ReadMode.TEXT

    # def _switch_mode_or_exit(self):
    #     Console.warn('Binary data detected, cannot proceed in text mode')
    #
    #     if not Settings.auto:
    #         Console.info('Use -b option to run in binary mode')
    #         App.exit(2)
    #
    #     if self._reader.reading_stdin:
    #         Console.info('Cannot repeat input stream reading because it\'s stdin')
    #         App.exit(3)
