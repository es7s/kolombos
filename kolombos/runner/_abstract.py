# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from abc import ABCMeta, abstractmethod


class AbstractRunner(metaclass=ABCMeta):
    @abstractmethod
    def run(self):
        pass
