from . import AbstractModeProcessor
from ..app import App
from ..byteio import ReadMode
from ..byteio.formatter import FormatterFactory
from ..byteio.parser import Parser
from ..byteio.reader import Reader
from kolombo.byteio.sequencer import Sequencer
from ..byteio.writer import Writer
from ..console import Console
from ..settings import Settings


class ByteIoProcessor(AbstractModeProcessor):
    def _init(self, read_mode: ReadMode):
        self._sequencer = Sequencer()
        self._reader = Reader(Settings.filename, self._process_chunk_buffered)
        self._parser = Parser(read_mode, self._sequencer)
        self._formatter = FormatterFactory.create(read_mode, self._sequencer)
        self._writer = Writer(self._sequencer)

    def invoke(self):
        try:
            self._init(self._get_read_mode_from_settings())
            self._reader.read()

        except UnicodeDecodeError:
            self._reader.close()
            self._switch_mode_or_exit()

            self._init(ReadMode.BINARY)
            self._reader.read()

    def _process_chunk_buffered(self, raw_input: bytes, offset: int, finish: bool):
        self._sequencer.append_raw(raw_input, offset, finish)
        self._parser.parse()
        self._formatter.format()
        self._writer.write()

    def _get_read_mode_from_settings(self) -> ReadMode:
        if Settings.binary:
            return ReadMode.BINARY
        elif Settings.text:
            return ReadMode.TEXT
        # auto:
        if Settings.debug > 0:
            return ReadMode.BINARY
        return ReadMode.TEXT

    def _switch_mode_or_exit(self):
        Console.warn('Binary data detected, cannot proceed in text mode')

        if not Settings.auto:
            Console.info('Use -b option to run in binary mode')
            App.exit(2)

        if self._reader.reading_stdin:
            Console.info('Cannot repeat input stream reading because it\'s stdin')
            App.exit(3)