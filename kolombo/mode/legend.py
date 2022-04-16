from os.path import join, dirname, realpath

from . import AbstractModeProcessor
from ..console import Console


class LegendModeProcessor(AbstractModeProcessor):
    LEGEND_FILENAME = 'legend.ansi'

    def invoke(self):
        with open(join(dirname(realpath(__file__)), '..', '..', 'legend.ansi'), 'rt') as f:
            Console.info(f.read())
