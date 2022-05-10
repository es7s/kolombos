# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------

from .template import Template

from .template_control import ControlCharGenericTemplate
from .template_printable import PrintableCharTemplate
from .template_utf8 import Utf8SequenceTemplate
from .template_newline import NewlineTemplate
from .template_escape import EscapeSequenceTemplate
from .template_escape_sgr import EscapeSequenceSGRTemplate

from .registry import TemplateRegistry
