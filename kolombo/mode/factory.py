from __future__ import annotations


from abc import ABCMeta, abstractmethod


class ModeProcessorFactory:
    @staticmethod
    def create() -> AbstractModeProcessor:
        from ..error import ArgumentError
        from ..settings import SettingsManager
        from .byteio import ByteIoProcessor
        from .legend import LegendModeProcessor
        from .version import VersionModeProcessor

        if SettingsManager.app_settings.legend:
            return LegendModeProcessor()
        elif SettingsManager.app_settings.version:
            return VersionModeProcessor()
        elif SettingsManager.app_settings.binary or SettingsManager.app_settings.text:
            return ByteIoProcessor()
        raise ArgumentError('No mode specified')


class AbstractModeProcessor(metaclass=ABCMeta):
    @abstractmethod
    def invoke(self):
        pass