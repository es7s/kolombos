# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from . import AbstractRunner
from ..byteio import ParserBuffer, Parser, Reader
from ..byteio.formatter import FormatterFactory
from ..byteio.segment import SegmentBuffer
from ..byteio.template import TemplateRegistry
from ..console import Console, ConsoleDebugBuffer
from ..settings import SettingsManager


# noinspection PyMethodMayBeStatic
class ByteIoRunner(AbstractRunner):
    def run(self):
        # try:
        self._reinit()
        self._reader.read()

        # except BinaryDataError:
        #    self._reader.close()
        #    self._switch_mode_or_exit()

        #    settings.binary = True ; settings.text = False
        #    self._reinit()
        #    self._reader.read()

    def _reinit(self):
        self._debug_buffer = ConsoleDebugBuffer()
        if not SettingsManager.app_settings.debug_settings:
            self._debug_buffer.write(1, Console.get_separator_line(main_open=True))

        self._parser_buffer = ParserBuffer()
        self._segment_buffer = SegmentBuffer()
        self._template_registry = TemplateRegistry()

        self._reader = Reader(SettingsManager.app_settings.filename, self._process_chunk_buffered)
        self._parser = Parser(self._parser_buffer, self._segment_buffer, self._template_registry)
        self._formatter = FormatterFactory.create(self._parser_buffer, self._segment_buffer)

    def _process_chunk_buffered(self, raw_input: bytes, offset: int, finish: bool):
        self._parser_buffer.append_raw(raw_input, finish)
        self._parser.parse(offset)
        self._formatter.format()

        self._debug_buffer.write(1, Console.get_separator_line(main_close=finish))


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
