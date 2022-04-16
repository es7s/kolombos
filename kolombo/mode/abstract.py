from abc import ABCMeta, abstractmethod


class AbstractModeProcessor(metaclass=ABCMeta):
    @abstractmethod
    def invoke(self):
        pass
