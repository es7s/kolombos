from __future__ import annotations

from . import AbstractModeProcessor, LegendModeProcessor, VersionModeProcessor, ByteIoProcessor
from .. import ArgumentError
from ..settings import SettingsManager


class ModeProcessorFactory:
    @staticmethod
    def create() -> AbstractModeProcessor:
        if SettingsManager.app_settings.legend:
            return LegendModeProcessor()
        elif SettingsManager.app_settings.version:
            return VersionModeProcessor()
        elif SettingsManager.app_settings.binary or SettingsManager.app_settings.text:
            return ByteIoProcessor()
        raise ArgumentError('No mode specified')

