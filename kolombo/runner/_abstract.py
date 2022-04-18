from abc import ABCMeta, abstractmethod


class AbstractRunner(metaclass=ABCMeta):
    @abstractmethod
    def run(self):
        pass
