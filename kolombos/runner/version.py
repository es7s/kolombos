# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
import re
from os.path import join, dirname, realpath, abspath

from . import AbstractRunner
from ..version import __version__
from ..console import Console


class VersionRunner(AbstractRunner):
    def run(self):
        Console.info(f'es7s/kolombos version {__version__}')
