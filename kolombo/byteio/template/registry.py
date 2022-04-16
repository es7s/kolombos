from pytermor import seq
from pytermor.seq import SequenceSGR

from . import Template, OpeningSeqPOV, LabelPOV, ControlCharGenericTemplate, Utf8SequenceTemplate, PrintableCharTemplate
from .. import CharClass, DisplayMode, ReadMode


class TemplateRegistry:
    def __init__(self):
        c_cc = CharClass.CONTROL_CHAR
        self.CONTROL_CHAR = ControlCharGenericTemplate(seq.RED, 'Ɐ')   # 0x01-0x07, 0x0e-0x1f
        self.CONTROL_CHAR_NULL = Template(c_cc, seq.HI_RED, 'Ø')       # 0x00
        self.CONTROL_CHAR_BACKSPACE = Template(c_cc, seq.RED, '←')     # 0x08
        self.CONTROL_CHAR_DELETE = Template(c_cc, seq.RED, '→')        # 0x7f
        self.CONTROL_CHAR_ESCAPE = Template(c_cc, seq.HI_YELLOW, 'Ǝ')  # 0x1b

        c_ws = CharClass.WHITESPACE
        op_ws = OpeningSeqPOV(seq.GRAY, {DisplayMode.FOCUSED: seq.BG_CYAN + seq.BLACK})
        self.WHITESPACE_TAB = Template(c_ws, op_ws, LabelPOV('⇥', {ReadMode.TEXT: '⇥\t'}))        # 0x09
        self.WHITESPACE_NEWLINE = Template(c_ws, op_ws, LabelPOV('↵', {ReadMode.TEXT: '↵\n'}))    # 0x0a  # ignored in text mode -> '\n'
        self.WHITESPACE_VERT_TAB = Template(c_ws, op_ws, '⤓')                                     # 0x0b
        self.WHITESPACE_FORM_FEED = Template(c_ws, op_ws, '↡')                                    # 0x0c
        self.WHITESPACE_CARR_RETURN = Template(c_ws, op_ws, '⇤')                                  # 0x0d
        self.WHITESPACE_SPACE = Template(c_ws, op_ws, LabelPOV('␣', {DisplayMode.FOCUSED: '·'}))  # 0x20

        self.UTF_8_SEQ = Utf8SequenceTemplate(seq.HI_BLUE, LabelPOV('ṳ', {ReadMode.BINARY: '▯'}))

        c_bin = CharClass.BINARY_DATA
        self.BINARY_DATA = Template(c_bin, seq.MAGENTA, LabelPOV('Ḇ', {ReadMode.BINARY: '▯'}))  # 0x80-0xff

        self.PRINTABLE_CHAR = PrintableCharTemplate(SequenceSGR(), '')  # 0x21-0x7e
