# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from os.path import dirname, abspath, join
from typing import List

from pytermor import *
from pytermor.util.stdlib_ext import *
from pytermor import SequenceSGR as SGR

from es7s_tpl_processor import Es7sTemplateProcessor
from kolombos.byteio import ReadMode as RM, DisplayMode as DM
from kolombos.byteio import MarkerDetailsEnum as MD
from kolombos.byteio.segment import Segment
from kolombos.byteio.template import (
    TemplateRegistry,
    Template,
    EscapeSequenceSGRTemplate,
    Utf8SequenceTemplate,
)
from kolombos.console import Console
from kolombos.settings import SettingsManager
from kolombos.version import __version__

project_dir = abspath(join(dirname(__file__), ".."))
TPL_PATH = join(project_dir, "dev", "legend.tpl.ansi")
OUTPUT_PATH = join(project_dir, "kolombos", "legend.ansi")

SettingsManager.init()
app_settings = SettingsManager.app_settings
reg = TemplateRegistry()
processor = Es7sTemplateProcessor()


def sanitize(s: str) -> str:
    return s.replace("\t", "").replace("\n", "")


def render_label(char: str, fg: str | None = 0xFFFFFF, bg: str | None = 0x000000, bold=True) -> str:
    return Style(fg=fg, bg=bg, bold=bold).render(" " + sanitize(char) + " ")


def invoke_default(
    t: Template,
    *raws: bytes,
    read_mode: RM = RM.BINARY,
    print_label: bool = True,
    print_hex: bool = True,
    marker: MD = MD.DEFAULT,
) -> str:
    result = [""] * 5

    if print_label:

        labels = []
        label_default_raw = t.label_stack.get(DM.DEFAULT, read_mode)
        if label_default_raw:
            label_default = render_label(label_default_raw)
        else:
            label_default = render_label("(*)", fg=0x666666, bg=None, bold=False)
        labels.append(label_default)

        label_focused_raw = t.label_stack.get(DM.FOCUSED, read_mode)
        label_focused = render_label(label_focused_raw)
        if label_focused_raw and label_focused_raw != label_default_raw:
            labels.append(label_focused)
        result[COL_LABEL] = "\x00".join(labels)

    if len(raws) == 1:
        raw = [raws[0], None, raws[0], None]
    elif len(raws) == 2:
        raw = [raws[0], None, raws[1], None]
    elif len(raws) == 3:
        raw = [raws[0], raws[1], raws[2], None]
    else:
        raw = list(raws)

    display_mode = DM.DEFAULT
    col_hex = COL_HEX_DEFAULT
    col_chr = COL_CHR_DEFAULT
    for idx, cur_raw in enumerate(raw):
        if idx == len(raw) // 2:
            display_mode = DM.FOCUSED
            col_hex = COL_HEX_FOCUSED
            col_chr = COL_CHR_FOCUSED

        if cur_raw:
            if print_hex:
                result[col_hex] += segs_to_hex(substitute_with(t, cur_raw, display_mode, RM.BINARY, marker))
            result[col_chr] += segs_to_processed(substitute_with(t, cur_raw, display_mode, read_mode, marker))

    # if raws == (b'',):
    #     for col in [COL_HEX_DEFAULT, COL_HEX_FOCUSED, COL_CHR_DEFAULT, COL_CHR_FOCUSED]:
    #         result[col] = Text(('--'*3)[:-1], style=Style(fg='gray')).render()
    return format_example(result)


def invoke_on_escape_sequences(
    t: Template,
    raw_or_seq: SGR | bytes,
    no_details: bool = False,
    brief_details: bool = False,
    full_details: bool = False,
    print_label=True,
    focus: bool = False,
    print_hex: bool = True,
    color_markers: bool = True,
    separators: bool = True,
) -> str:
    if isinstance(raw_or_seq, SGR):
        raw = raw_or_seq.assemble().encode()
        sgr_params_str = ReplaceSGR("\\3").apply(raw_or_seq.assemble()).encode()
    else:
        raw = raw_or_seq
        sgr_params_str = None
    dm = DM.FOCUSED if focus else DM.DEFAULT
    kwargs = dict(
        color_markers=color_markers,
        separators=separators,
        details_fmt_str=sgr_params_str,
    )

    label = ""
    if print_label:
        label = render_label(t.label_stack.get())

    result_hex = None
    if print_hex:
        result_hex = segs_to_hex(substitute_with(t, raw, dm, RM.BINARY, **kwargs))
        result_hex = rjust_sgr(result_hex, 12) + " "

    md = MD.BRIEF_DETAILS
    if no_details:
        md = MD.NO_DETAILS
    elif full_details:
        md = MD.FULL_DETAILS
    result_chr = [segs_to_processed(substitute_with(t, raw, dm, RM.TEXT, md, **kwargs))]
    result_chr_cols = center_sgr("  ".join(result_chr), 10, " "), None
    return format_example([label, result_hex, None, *result_chr_cols])


def invoke_on_utf8(
    t: Template,
    *raws: bytes,
    read_mode: RM = RM.BINARY,
    print_label: bool = False,
    print_hex: bool = False,
    decode: bool = False,
    shift: int = 0,
) -> str:
    label = ""
    if print_label:
        if decode:
            label = render_label(Utf8SequenceTemplate.DECODED_LEFT_FILL_CHAR)
        elif read_mode.is_text:
            label = render_label("(*)", fg=0x666666, bg=None, bold=False)
        else:
            label = render_label(t.label_stack.get(RM.BINARY))

    raw = list(raws)
    hex_segs = []
    result_chr = []
    for idx, cur_raw in enumerate(raw):
        dm = DM.FOCUSED if idx > 0 else DM.DEFAULT
        if print_hex:
            hex_segs += substitute_with(t, cur_raw, dm, read_mode, decode=decode)
        result_chr += [segs_to_processed(substitute_with(t, cur_raw, dm, read_mode, decode=decode))]

    result_hex = ljust_sgr(segs_to_hex(hex_segs), 13)
    result_chr = " " * shift + center_sgr(" ".join(result_chr), 8)

    return format_example([label, result_hex, None, result_chr, None])


def substitute_with(
    t: Template,
    raw: bytes,
    display_mode: DM,
    read_mode: RM,
    marker_details: MD = MD.BRIEF_DETAILS,
    decode: bool = False,
    color_markers: bool = False,
    separators: bool = True,
    details_fmt_str: bytes = None,
) -> List[Segment]:

    app_settings.text = read_mode.is_text
    app_settings.binary = not app_settings.text
    setattr(app_settings, f"focus_{t.char_class.value}", display_mode.is_focused)
    app_settings.marker = marker_details.value
    app_settings.decode = decode
    app_settings.color_markers = color_markers
    app_settings.no_separators = not separators

    t.update_settings()
    if isinstance(t, EscapeSequenceSGRTemplate) and details_fmt_str is not None:
        t.set_details_fmt_str(details_fmt_str)
    return t.substitute(raw)


def segs_to_hex(segs: List[Segment]) -> str:
    max_b = 4
    cur_b = 0
    excessive = False
    result = ""
    for seg in segs:
        cur_raw = seg.raw[: max_b - cur_b]
        cur_hex = cur_raw.hex(" ")
        if len(cur_raw) > 0 and len(seg.raw) + cur_b > max_b:
            cur_hex = cur_hex[:-1]
            excessive = True
        result += Span(seg.opening_seq)(" " + cur_hex)
        cur_b += len(cur_raw)
        if cur_b >= max_b:
            break
    if excessive:
        result += "‥"
    return result


def segs_to_processed(segs: List[Segment]) -> str:
    return "".join([Span(seg.opening_seq)(sanitize(seg.processed)) for seg in segs])


def format_example(col_values: list) -> str:
    result = " " * PADDING_LEFT
    for col in COLS_ORDER:
        if col_values[col] is not None:
            result += COL_FORMATTERS[col](col_values[col])

    result += " " * PADDING_RIGHT
    return result


COL_LABEL = 0
COL_HEX_DEFAULT = 1
COL_HEX_FOCUSED = 2
COL_CHR_DEFAULT = 3
COL_CHR_FOCUSED = 4

COLS_ORDER = [
    COL_LABEL,
    COL_CHR_DEFAULT,
    COL_CHR_FOCUSED,
    COL_HEX_DEFAULT,
    COL_HEX_FOCUSED,
]
COL_FORMATTERS = {
    COL_LABEL: lambda s: center_sgr(" ".join(s.split("\x00")), 7),
    COL_CHR_DEFAULT: lambda s: rjust_sgr(s, 5) + " ",
    COL_CHR_FOCUSED: lambda s: ljust_sgr(s, 5),
    COL_HEX_DEFAULT: lambda s: rjust_sgr(s, 6),
    COL_HEX_FOCUSED: lambda s: rjust_sgr(s, 6) + " ",
}
PADDING_LEFT = 0
PADDING_RIGHT = 3

ESQ_SGR0 = reg.ESCAPE_SEQ_SGR_0
ESQ_SGR = reg.ESCAPE_SEQ_SGR
idef = invoke_default
iesq = invoke_on_escape_sequences
iutf = invoke_on_utf8
initc256 = SGR.init_color_indexed
initcrgb = SGR.init_color_rgb
enc = lambda s: s.encode("utf-8")
crgb2 = initcrgb(0xAA, 0x6A, 0x6A)
VARIABLES = {
    "ver": __version__,
    "ex_s_tab": idef(reg.WHITESPACE_TAB, b"\x09"),
    "ex_s_lf": idef(reg.WHITESPACE_NEWLINE, b"\x0a"),
    "ex_s_vtab": idef(reg.WHITESPACE_VERT_TAB, b"\x0b"),
    "ex_s_ff": idef(reg.WHITESPACE_FORM_FEED, b"\x0c"),
    "ex_s_cr": idef(reg.WHITESPACE_CARR_RETURN, b"\x0d"),
    "ex_s_space": idef(reg.WHITESPACE_SPACE, b"\x20"),
    "ex_c_misc0": idef(reg.CONTROL_CHAR, b"\x03", b"\x1a"),
    "ex_c_misc1": idef(
        reg.CONTROL_CHAR,
        b"\x03",
        b"\x1a",
        read_mode=RM.TEXT,
        print_label=False,
        print_hex=False,
        marker=MD.BRIEF_DETAILS,
    ),
    "ex_c_misc2": idef(
        reg.CONTROL_CHAR,
        b"\x03",
        b"\x1a",
        print_label=False,
        print_hex=False,
        read_mode=RM.TEXT,
        marker=MD.FULL_DETAILS,
    ),
    "ex_c_null": idef(reg.CONTROL_CHAR_NULL, b"\x00"),
    "ex_c_bskpc": idef(reg.CONTROL_CHAR_BACKSPACE, b"\x08"),
    "ex_c_del": idef(reg.CONTROL_CHAR_DELETE, b"\x7f"),
    "ex_c_esc": idef(reg.CONTROL_CHAR_ESCAPE, b"\x1b"),
    "ex_p_print": idef(reg.PRINTABLE_CHAR, b"!", b'"', b"1", b"2"),
    "ex_p_print2": idef(reg.PRINTABLE_CHAR, b"A", b"B", b"}", b"~", print_label=False),
    "ex_e_reset_lbl": idef(ESQ_SGR0, b""),
    "ex_e_reset_m0": iesq(ESQ_SGR0, Seqs.RESET, no_details=True),
    "ex_e_reset_m1": iesq(ESQ_SGR0, Seqs.RESET, brief_details=True, print_label=False),
    "ex_e_reset_m2": iesq(ESQ_SGR0, Seqs.RESET, full_details=True, print_label=False),
    "ex_e_sgr_lbl": idef(ESQ_SGR, b""),
    "ex_e_sgr_m0": iesq(ESQ_SGR, SGR(34), no_details=True, print_label=True, color_markers=False),
    "ex_e_sgr_m0c": iesq(ESQ_SGR, SGR(33), no_details=True, print_label=False),
    "ex_e_sgr_m1": iesq(ESQ_SGR, SGR(93, 1), brief_details=True, print_label=False),
    "ex_e_sgr_m1_2": iesq(ESQ_SGR, initc256(88) + initc256(16, True), brief_details=True, print_label=False),
    "ex_e_sgr_m1_3": iesq(ESQ_SGR, crgb2, brief_details=True, print_label=False, print_hex=True),
    "ex_e_sgr_m2": iesq(ESQ_SGR, crgb2, full_details=True, print_label=False, print_hex=False, color_markers=False),
    "ex_e_csi": iesq(reg.ESCAPE_SEQ_CSI, b"\x1b\x5b\x32\x34\x64", full_details=True),
    "ex_e_nf": iesq(reg.ESCAPE_SEQ_NF, b"\x1b\x28\x42", full_details=True, focus=True),
    "ex_e_fp": iesq(reg.ESCAPE_SEQ_FP, b"\x1b\x32", full_details=True, focus=True),
    "ex_e_fe": iesq(reg.ESCAPE_SEQ_FE, b"\x1b\x47", brief_details=True),
    "ex_e_fs": iesq(reg.ESCAPE_SEQ_FS, b"\x1b\x73", no_details=True),
    "ex_u_lbl": idef(reg.UTF_8_SEQ, b""),
    "ex_u_1": idef(reg.UTF_8_SEQ, b"\xd1", b"\x85", b"\xd0", b"\xb9", print_label=True),
    "ex_u_2": iutf(reg.UTF_8_SEQ, enc("ы"), enc("世"), print_hex=True, decode=True, shift=1, print_label=True),
    "ex_u_3": iutf(reg.UTF_8_SEQ, enc("🐍"), read_mode=RM.TEXT, print_hex=True, shift=1, print_label=True),
    "ex_i_1": idef(reg.BINARY_DATA, b"\xee", b"\xb0", b"\xc0", b"\xcc"),
    "ex_i_2": idef(reg.BINARY_DATA, b"\xc0", b"\xff", b"\xee", b"\xda", read_mode=RM.TEXT, print_label=True),
    "separator": 87 * Style(fg=0x333333).render("─"),
    "fmt_header": Seqs.HI_WHITE + Seqs.BOLD,
    "fmt_thead": Seqs.DIM + Seqs.UNDERLINED,
    "fmt_cc": Seqs.BOLD,
    "fmt_comment": Seqs.GRAY,
    "fmt_param": Seqs.DIM + Seqs.BOLD,
    "fmt_m1": initc256(117),
    "fmt_m2": initcrgb(248, 184, 137),
}

with open(TPL_PATH, "rt", encoding="utf8") as f:
    tpl = f.read()

out = processor.substitute(tpl, VARIABLES)
if not out.endswith("\n"):
    out += "\n"
out += f"# Generated at {datetime.now():%e-%b-%y %R}"


def format_thousand_sep(value: int | float, separator=" "):
    return f"{value:_}".replace("_", separator)


with open(OUTPUT_PATH, "wt", encoding="utf8") as f:
    length = f.write(out)
    Console.info(f"Wrote {Spans.BOLD(format_thousand_sep(length))} bytes to {Spans.BLUE(OUTPUT_PATH)}")
