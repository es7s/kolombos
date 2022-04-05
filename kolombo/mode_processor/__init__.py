from __future__ import annotations

from ..settings import Settings


class ModeProcessorFactory:
    @staticmethod
    def create() -> AbstractModeProcessor:
        from .byteio import ByteIoProcessor
        from .legend import LegendModeProcessor

        if Settings.legend:
            return LegendModeProcessor()
        return ByteIoProcessor()


class AbstractModeProcessor:
    def invoke(self):
        pass
