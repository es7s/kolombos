# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from importlib import resources

from pytermor import Spans
from ..byteio import ReadMode
from ..settings import SettingsManager
from ..console import Console
from . import AbstractRunner, ByteIoRunner


class DemoRunner(AbstractRunner):
    DEMO_FILENAME = 'demo.bin'

    def run(self):
        with resources.path('kolombos', self.DEMO_FILENAME) as path:
            aps = SettingsManager.app_settings
            aps.filename = path
            aps.set_default_read_mode(ReadMode.BINARY)
            if aps.decode is None:
                aps.decode = True
            if aps.columns is None:
                aps.columns = 32
            ByteIoRunner().run()
        Console.info("\nRun the app with '"+Spans.BOLD('--legend')+"' option to learn how to read the output")
