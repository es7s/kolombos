from __future__ import annotations

import sys
import traceback

from pytermor import fmt
from pytermor.fmt import Format

from .arghelp import AppArgumentParser
from .mode_processor import ModeProcessorFactory
from .settings import Settings


# noinspection PyMethodMayBeStatic
class App:
    def run(self):
        try:
            self._parse_args()  # help processing is handled by argparse
            (ModeProcessorFactory.create()).invoke()
        except Exception as e:
            (ExceptionHandler()).handle(e)
            self.exit(1)
        self.exit()

    def _parse_args(self):
        AppArgumentParser().parse_args(namespace=Settings)
        Settings.set_defaults()

    @staticmethod
    def exit(code: int = 0):
        print()
        exit(code)


class ExceptionHandler:
    def __init__(self):
        self.format: Format = fmt.red

    def handle(self, e: Exception):
        if Settings.debug > 0:
            self._log_traceback(e)
        else:
            self._write(f'ERROR: {e.__class__.__name__}: {e!s}')
            print("Run the app with '--debug' argument to see the details")

    def _write(self, s: str):
        print(self.format(s), file=sys.stderr)

    def _log_traceback(self, e: Exception):
        ex_traceback = e.__traceback__
        tb_lines = [line.rstrip('\n')
                    for line
                    in traceback.format_exception(e.__class__, e, ex_traceback)]
        self._write("\n".join(tb_lines))
