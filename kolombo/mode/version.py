import re
from os.path import join, dirname, realpath, abspath

from . import AbstractModeProcessor
from ..console import Console


class VersionModeProcessor(AbstractModeProcessor):
    def invoke(self):
        with open(join(dirname(realpath(__file__)), '..', '..', '.env.dist'), 'rt') as f:
            Console.debug(f"Reading '{abspath(f.name)}'", 1)
            for line in f.readlines():
                if version := re.match(r'^VERSION\s*=\s*(.+)$', line):
                    Console.info(version.group(1))
                    return
            raise RuntimeError('Could not find version in .env file')
