from . import AbstractFormatter, BinaryFormatter, TextFormatter
from .. import ReadMode
from ...settings import SettingsManager


class FormatterFactory:
    @staticmethod
    def create(*args) -> AbstractFormatter:
        read_mode = SettingsManager.app_settings.read_mode
        if read_mode is ReadMode.TEXT:
            return TextFormatter(*args)
        elif read_mode is ReadMode.BINARY:
            return BinaryFormatter(*args)
        raise RuntimeError(f'Invalid read mode {read_mode}')
