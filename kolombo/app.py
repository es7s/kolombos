from __future__ import annotations

from .arghelp import AppArgumentParser
from .console import Console
from .mode import ModeProcessorFactory
from .settings import Settings


# noinspection PyMethodMayBeStatic
from .util import println


class App:
    def run(self):
        try:
            self._parse_args()  # help processing is handled by argparse
            (ModeProcessorFactory.create()).invoke()
        except Exception as e:
            Console.on_exception(e)
            self.exit(1)
        self.exit()

    def _parse_args(self):
        AppArgumentParser().parse_args(namespace=Settings)
        Settings.set_defaults()

    @staticmethod
    def exit(code: int = 0):
        println()
        exit(code)
