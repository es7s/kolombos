# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from pytermor import SequenceSGR, Seqs, ansi

from . import Template, ControlCharGenericTemplate, Utf8SequenceTemplate, \
    PrintableCharTemplate, NewlineTemplate, EscapeSequenceTemplate, EscapeSequenceSGRTemplate
from .. import CharClass, DisplayMode, ReadMode, LabelPOV, OpeningSeqPOV


class TemplateRegistry:
    def __init__(self):
        c_cc = CharClass.CONTROL_CHAR
        self.CONTROL_CHAR = ControlCharGenericTemplate(Seqs.RED, 'Ɐ')   # 0x01-0x07, 0x0e-x1a, 0x1c-0x1f
        self.CONTROL_CHAR_NULL = Template(c_cc, Seqs.HI_RED, 'Ø')       # 0x00
        self.CONTROL_CHAR_BACKSPACE = Template(c_cc, Seqs.RED, '←')     # 0x08
        self.CONTROL_CHAR_DELETE = Template(c_cc, Seqs.RED, '→')        # 0x7f
        self.CONTROL_CHAR_ESCAPE = Template(c_cc, Seqs.HI_YELLOW, '∌')  # 0x1b

        c_ws = CharClass.WHITESPACE
        op_ws: OpeningSeqPOV = OpeningSeqPOV(Seqs.HI_CYAN, {DisplayMode.FOCUSED: Seqs.BG_CYAN + Seqs.BLACK})
        self.WHITESPACE_TAB = Template(c_ws, op_ws, LabelPOV('⇥', {ReadMode.TEXT: '⇥\t'}))        # 0x09
        self.WHITESPACE_NEWLINE = NewlineTemplate(op_ws, '↵')                                     # 0x0a
        self.WHITESPACE_VERT_TAB = Template(c_ws, op_ws, '⤓')                                     # 0x0b
        self.WHITESPACE_FORM_FEED = Template(c_ws, op_ws, '↡')                                    # 0x0c
        self.WHITESPACE_CARR_RETURN = Template(c_ws, op_ws, '⇤')                                  # 0x0d @FIXME #13
        self.WHITESPACE_SPACE = Template(c_ws, op_ws, LabelPOV('␣', {DisplayMode.FOCUSED: '·'}))  # 0x20

        self.ESCAPE_SEQ_SGR_0 = EscapeSequenceTemplate(SequenceSGR.init_color_indexed(255) +
                                                       SequenceSGR.init_color_indexed(16, True), 'θ')  # \e[m
        self.ESCAPE_SEQ_SGR = EscapeSequenceSGRTemplate(SequenceSGR.init_color_indexed(210) +
                                                        SequenceSGR.init_color_indexed(16, True), 'ǝ')  # \e[ (0x30-3f) (0x20-2f) m
        self.ESCAPE_SEQ_CSI = EscapeSequenceTemplate(Seqs.HI_GREEN, 'Ͻ')   # \e[ (0x30-3f) (0x20-2f) ...
        self.ESCAPE_SEQ_NF = EscapeSequenceTemplate(Seqs.GREEN, 'ꟻ')       # \e (0x20-2f) ...
        self.ESCAPE_SEQ_FP = EscapeSequenceTemplate(Seqs.YELLOW, 'ꟼ')      # \e (0x30-3f)
        self.ESCAPE_SEQ_FE = EscapeSequenceTemplate(Seqs.YELLOW, 'Ǝ')      # \e (0x40-5f)
        self.ESCAPE_SEQ_FS = EscapeSequenceTemplate(Seqs.YELLOW, 'Ꙅ')      # \e (0x60-7e)

        self.UTF_8_SEQ = Utf8SequenceTemplate(Seqs.HI_BLUE, LabelPOV('', {ReadMode.BINARY: '▯'}))

        c_bin = CharClass.BINARY_DATA
        self.BINARY_DATA = Template(c_bin, Seqs.MAGENTA, LabelPOV('Ḇ', {ReadMode.BINARY: '▯'}))  # 0x80-0xff

        op_pr: OpeningSeqPOV = OpeningSeqPOV(SequenceSGR.init_color_indexed(102), {DisplayMode.FOCUSED: Seqs.BG_WHITE + Seqs.BLACK})
        self.PRINTABLE_CHAR = PrintableCharTemplate(op_pr, '')  # 0x21-0x7e
