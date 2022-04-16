from abc import ABCMeta, abstractmethod


class Chainable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def data_len(self) -> int: raise NotImplementedError

    @property
    @abstractmethod
    def is_newline(self) -> bool: raise NotImplementedError