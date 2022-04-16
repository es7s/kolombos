from . import AbstractModeProcessor
from ..byteio import ReadMode
from ..byteio.formatter import FormatterFactory
from ..byteio.parser import Parser
from ..byteio.parser_buf import ParserBuffer
from ..byteio.reader import Reader
from ..byteio.segment.buffer import SegmentBuffer
from ..console import Console, ConsoleDebugBuffer
from ..settings import SettingsManager


# noinspection PyMethodMayBeStatic
class ByteIoProcessor(AbstractModeProcessor):
    def _init(self, read_mode: ReadMode):
        self._debug_buffer = ConsoleDebugBuffer()
        if not SettingsManager.app_settings.debug_settings:
            self._debug_buffer.write(1, Console.get_separator_line(main_open=True))

        self._parser_buffer = ParserBuffer()
        self._segment_buffer = SegmentBuffer()

        self._reader = Reader(SettingsManager.app_settings.filename, self._process_chunk_buffered)
        self._parser = Parser(read_mode, self._parser_buffer, self._segment_buffer)
        self._formatter = FormatterFactory.create(read_mode, self._parser_buffer, self._segment_buffer)

    def invoke(self):
        # try:
        self._init(self._get_read_mode_from_settings())
        self._reader.read()

        # except BinaryDataError:
        #    self._reader.close()
        #    self._switch_mode_or_exit()

        #    self._init(ReadMode.BINARY)
        #    self._reader.read()

    def _process_chunk_buffered(self, raw_input: bytes, offset: int, finish: bool):
        self._parser_buffer.append_raw(raw_input, finish)
        self._parser.parse(offset)
        self._formatter.format()

        self._debug_buffer.write(1, Console.get_separator_line(main_close=finish))

    def _get_read_mode_from_settings(self) -> ReadMode:
        if SettingsManager.app_settings.binary:
            return ReadMode.BINARY
        elif SettingsManager.app_settings.text:
            return ReadMode.TEXT
        # auto:
        return ReadMode.TEXT

    # def _switch_mode_or_exit(self):
    #     Console.warn('Binary data detected, cannot proceed in text mode')
    #
    #     if not SettingsManager.app_settings.auto:
    #         Console.info('Use -b option to run in binary mode')
    #         App.exit(2)
    #
    #     if self._reader.reading_stdin:
    #         Console.info('Cannot repeat input stream reading because it\'s stdin')
    #         App.exit(3)
