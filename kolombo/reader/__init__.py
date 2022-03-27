import abc
from typing import Optional

from ..formatter import AbstractFormatter


class AbstractReader(metaclass=abc.ABCMeta):
    _filename: Optional[str]
    _io: Optional
    _formatter: AbstractFormatter
    _offset: int = 0

    def __init__(self, filename: Optional[str], formatter: AbstractFormatter):
        self._filename = filename
        self._formatter = formatter

    def read(self):
        self._open()
        try:
            self._read_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self._close()

    @abc.abstractmethod
    def _open(self) -> None: raise NotImplementedError

    @abc.abstractmethod
    def _read_loop(self) -> None: raise NotImplementedError

    @property
    def _is_arg_stdin(self) -> bool:
        return not self._filename or self._filename == '-'

    def _close(self):
        if self._io and not self._io.closed:
            self._io.close()
