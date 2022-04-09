from __future__ import annotations

from abc import abstractmethod, ABCMeta


class ModeProcessorFactory:
    @staticmethod
    def create() -> AbstractModeProcessor:
        from ..error import ArgumentError
        from ..settings import Settings
        from .byteio import ByteIoProcessor
        from .legend import LegendModeProcessor
        from .version import VersionModeProcessor

        if Settings.legend:
            return LegendModeProcessor()
        elif Settings.version:
            return VersionModeProcessor()
        elif Settings.binary or Settings.text or Settings.auto:
            return ByteIoProcessor()
        raise ArgumentError('No mode specified')


class AbstractModeProcessor(metaclass=ABCMeta):
    @abstractmethod
    def invoke(self):
        pass
