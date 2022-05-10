# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from abc import ABCMeta, abstractmethod


class Chainable(metaclass=ABCMeta):
    @property
    @abstractmethod
    def data_len(self) -> int: raise NotImplementedError

    @property
    @abstractmethod
    def is_newline(self) -> bool: raise NotImplementedError
