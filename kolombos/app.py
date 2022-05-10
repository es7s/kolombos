# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from . import AppArgumentParser
from .console import Console
from .runner import RunnerFactory
from .settings import SettingsManager


# noinspection PyMethodMayBeStatic
class App:
    def run(self):
        try:
            self._parse_args()  # help processing is handled by argparse
            (RunnerFactory.create()).run()
        except Exception as e:
            Console.on_exception(e)
            self.exit(1)
        self.exit()

    def _parse_args(self):
        SettingsManager.init()
        AppArgumentParser().parse_args(namespace=SettingsManager.app_settings)
        Console.debug_settings()

    @staticmethod
    def exit(code: int = 0):
        print()
        exit(code)
