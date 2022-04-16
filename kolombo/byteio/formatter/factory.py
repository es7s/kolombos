from kolombo.byteio.formatter.abstract import AbstractFormatter
from kolombo.byteio.read_mode import ReadMode
from kolombo.settings import SettingsManager


class FormatterFactory:
    @staticmethod
    def create(*args) -> AbstractFormatter:
        from .binary import BinaryFormatter
        from .text import TextFormatter

        read_mode = SettingsManager.app_settings.read_mode
        if read_mode is ReadMode.TEXT:
            return TextFormatter(*args)
        elif read_mode is ReadMode.BINARY:
            return BinaryFormatter(*args)
        raise RuntimeError(f'Invalid read mode {read_mode}')
