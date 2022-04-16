from __future__ import annotations

from pytermor.seq import SequenceSGR

from .arghelp import AppArgumentParser
from .console import Console
from .mode import ModeProcessorFactory
from .settings import SettingsManager
from .util import println


# noinspection PyMethodMayBeStatic

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
        SettingsManager.init()
        AppArgumentParser().parse_args(namespace=SettingsManager.app_settings)
        SettingsManager.debug_print_values()

    @staticmethod
    def exit(code: int = 0):
        println()
        exit(code)
