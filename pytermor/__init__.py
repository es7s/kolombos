# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from .ansi import IntCodes, Seqs, Spans, SequenceSGR, Span, NOOP_SEQ, NOOP_SPAN
from .color import Colors, ColorIndexed16, ColorIndexed256, ColorRGB, NOOP_COLOR
from .render import Styles, Style, Text, SgrRenderer, RendererManager, NOOP_STYLE
from ._version import __version__

import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
