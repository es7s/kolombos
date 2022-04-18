from os.path import join, dirname, realpath

from . import AbstractRunner
from ..console import Console


class LegendRunner(AbstractRunner):
    LEGEND_FILENAME = 'legend.ansi'

    def run(self):
        with open(join(dirname(realpath(__file__)), '..', '..', 'legend.ansi'), 'rt') as f:
            Console.info(f.read())
