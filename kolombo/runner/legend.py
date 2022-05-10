# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from importlib.resources import read_text

from . import AbstractRunner
from ..console import Console


class LegendRunner(AbstractRunner):
    LEGEND_FILENAME = 'legend.ansi'

    def run(self):
        for line in read_text('kolombo', self.LEGEND_FILENAME).splitlines(keepends=True):
            if line.startswith('#'):
                continue
            Console.info(line, end='')
