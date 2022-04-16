import re
from os.path import join, dirname, realpath, abspath

from .factory import AbstractModeProcessor
from ..console import Console, ConsoleDebugBuffer


class VersionModeProcessor(AbstractModeProcessor):
    def invoke(self):
        with open(join(dirname(realpath(__file__)), '..', '..', '.env.dist'), 'rt') as f:
            ConsoleDebugBuffer().write(1, f"Reading '{abspath(f.name)}'")
            for line in f.readlines():
                if version := re.match(r'^VERSION\s*=\s*(.+)$', line):
                    Console.info(version.group(1))
                    return
            raise RuntimeError('Could not find version in .env file')
