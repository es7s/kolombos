# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from os.path import dirname, abspath, join
from typing import List

from pytermor import seq, autof, ReplaceSGR, SequenceSGR, sgr, ljust_fmtd, rjust_fmtd, center_fmtd

from es7s_tpl_processor import Es7sTemplateProcessor
from kolombo.byteio import ReadMode, DisplayMode, MarkerDetailsEnum
from kolombo.byteio.segment import Segment
from kolombo.byteio.template import TemplateRegistry, Template, EscapeSequenceSGRTemplate
from kolombo.console import Console
from kolombo.settings import SettingsManager
from kolombo.version import __version__

project_dir = abspath(join(dirname(__file__), '..'))
TPL_PATH = join(project_dir, 'dev', 'legend.tpl.ansi')
OUTPUT_PATH = join(project_dir, 'legend.ansi')

SettingsManager.init()
app_settings = SettingsManager.app_settings
reg = TemplateRegistry()
processor = Es7sTemplateProcessor()


def sanitize(s: str) -> str:
    return s.replace('\t', '').replace('\n', '')


def invoke_default(t: Template, *raws: bytes, read_mode: ReadMode = ReadMode.BINARY,
                   marker: MarkerDetailsEnum = MarkerDetailsEnum.DEFAULT) -> str:
    result = ['']*5

    labels = [sanitize(t._label_stack.get(DisplayMode.DEFAULT, ReadMode.BINARY))]
    label_text = sanitize(t._label_stack.get(DisplayMode.DEFAULT, ReadMode.TEXT))
    label_focused = sanitize(t._label_stack.get(DisplayMode.FOCUSED, ReadMode.BINARY))
    if label_text and label_text not in labels:
        labels.append(label_text)
    if label_focused and label_focused not in labels:
        labels.append(label_focused)
    result[COL_LABEL] = ' '.join(labels)

    if len(raws) == 1:
        raw = [raws[0], None, raws[0], None]
    elif len(raws) == 2:
        raw = [raws[0], None, raws[1], None]
    elif len(raws) == 3:
        raw = [raws[0], raws[1], raws[2], None]
    else:
        raw = list(raws)

    display_mode = DisplayMode.DEFAULT
    col_hex = COL_HEX_DEFAULT
    col_chr = COL_CHR_DEFAULT
    for idx, cur_raw in enumerate(raw):
        if idx == len(raw) // 2:
            display_mode = DisplayMode.FOCUSED
            col_hex = COL_HEX_FOCUSED
            col_chr = COL_CHR_FOCUSED

        if cur_raw:
            result[col_hex] += segs_to_hex(substitute_with(t, cur_raw, display_mode, ReadMode.BINARY, marker))
            result[col_chr] += segs_to_processed(substitute_with(t, cur_raw, display_mode, read_mode, marker))

    return format_example(result)


def invoke_on_escape_sequences(t: Template, seq: SequenceSGR | bytes, no_details: bool = False,
                               brief_details: bool = False, full_details: bool = False, focus: bool = False) -> str:
    if isinstance(seq, SequenceSGR):
        raw = seq.print().encode()
        sgr_params_str = ReplaceSGR('\\3').apply(seq.print())
    else:
        raw = seq
        sgr_params_str = None
    dm = DisplayMode.FOCUSED if focus else DisplayMode.DEFAULT

    label = t._label_stack.get()
    hex = segs_to_hex(substitute_with(t, raw, dm, ReadMode.BINARY, details_fmt_str=sgr_params_str))

    processed = []
    if no_details:
        processed.append(segs_to_processed(substitute_with(t, raw, dm, ReadMode.TEXT, MarkerDetailsEnum.NO_DETAILS,
                                                           details_fmt_str=sgr_params_str)))
    elif brief_details:
        processed.append(segs_to_processed(
            substitute_with(t, raw, dm, ReadMode.TEXT, MarkerDetailsEnum.BRIEF_DETAILS,
                            details_fmt_str=sgr_params_str)))
    elif full_details:
        processed.append(segs_to_processed(
            substitute_with(t, raw, dm, ReadMode.TEXT, MarkerDetailsEnum.FULL_DETAILS, details_fmt_str=sgr_params_str)))

    hex = rjust_fmtd(hex, 12, ' ')
    processed_cols = center_fmtd('  '.join(processed), 10, '.'), None

    return format_example([label, hex, None, *processed_cols])


def invoke_on_utf8(t: Template, raw: bytes, read_mode: ReadMode, print_label: bool = False, print_hex: bool = False,
                   decode: bool = False, focus: bool = False, processed_shift: int = 0) -> str:
    label = ''
    if print_label:
        label = t._label_stack.get(ReadMode.BINARY)

    raws = [raw]
    if focus:
        raws = [raw[:2], raw[2:]]

    hex = ''
    processed = ''
    for idx, cur_raw in enumerate(raws):
        dm = DisplayMode.FOCUSED if idx > 0 else DisplayMode.DEFAULT
        if print_hex:
            hex += segs_to_hex(substitute_with(t, cur_raw, dm, read_mode, decode=decode))
        processed += segs_to_processed(substitute_with(t, cur_raw, dm, read_mode, decode=decode))

    hex = ljust_fmtd(hex, 12)
    processed = center_fmtd(processed, 8, '.')

    return format_example([label, hex, None, processed, None])


def substitute_with(t: Template, raw: bytes, display_mode: DisplayMode, read_mode: ReadMode,
                    marker_details: MarkerDetailsEnum = MarkerDetailsEnum.BRIEF_DETAILS,
                    decode: bool = False, details_fmt_str: str = None) -> List[Segment]:
    app_settings.text = read_mode.is_text
    app_settings.binary = not app_settings.text
    setattr(app_settings, f'focus_{t._char_class.value}', display_mode.is_focused)
    app_settings.marker = marker_details.value
    app_settings.decode = decode

    t.update_settings()
    if isinstance(t, EscapeSequenceSGRTemplate) and details_fmt_str is not None:
        t.set_details_fmt_str(details_fmt_str)

    return t.substitute(raw)


def segs_to_hex(segs: List[Segment]) -> str:
    max_b = 4
    cur_b = 0
    excessive = False
    hex = ''
    for seg in segs:
        cur_raw = seg.raw[:max_b - cur_b]
        cur_hex = cur_raw.hex(' ')
        if len(cur_raw) > 0 and len(seg.raw) > cur_b + max_b:
            cur_hex = cur_hex[:-1]
            excessive = True
        hex += autof(seg.opening_seq)(' ' + cur_hex)
        cur_b += len(cur_raw)
        if cur_b >= max_b:
            break
    if excessive:
        hex += '‥'
    return hex


def segs_to_processed(segs: List[Segment]) -> str:
    return ''.join([autof(seg.opening_seq)(sanitize(seg.processed)) for seg in segs])


def format_example(col_values: list) -> str:
    result = ''
    for col in COLS:
        if col_values[col] is not None:
            result += COL_FORMATTERS[col](col_values[col])

    result += ' '
    return result


COL_LABEL = 0
COL_HEX_DEFAULT = 1
COL_HEX_FOCUSED = 2
COL_CHR_DEFAULT = 3
COL_CHR_FOCUSED = 4

COLS = [
    COL_LABEL,
    COL_HEX_DEFAULT,
    COL_HEX_FOCUSED,
    COL_CHR_DEFAULT,
    COL_CHR_FOCUSED,
]
COL_FORMATTERS = {
    COL_LABEL: lambda s: center_fmtd(s, 5),
    COL_HEX_DEFAULT: lambda s: rjust_fmtd(s, 6),
    COL_HEX_FOCUSED: lambda s: rjust_fmtd(s, 6),
    COL_CHR_DEFAULT: lambda s: rjust_fmtd(s, 5) + ' ',
    COL_CHR_FOCUSED: lambda s: ljust_fmtd(s, 5)
}

VARIABLES = {
    'ver': __version__,
    'ex_s_tab': invoke_default(reg.WHITESPACE_TAB, b'\x09'),
    'ex_s_lf': invoke_default(reg.WHITESPACE_NEWLINE, b'\x0a'),
    'ex_s_vtab': invoke_default(reg.WHITESPACE_VERT_TAB, b'\x0b'),
    'ex_s_ff': invoke_default(reg.WHITESPACE_FORM_FEED, b'\x0c'),
    'ex_s_cr': invoke_default(reg.WHITESPACE_CARR_RETURN, b'\x0d'),
    'ex_s_space': invoke_default(reg.WHITESPACE_SPACE, b'\x20'),

    'ex_c_misc0': invoke_default(reg.CONTROL_CHAR, b'\x01', b'\x02'),
    'ex_c_misc1': invoke_default(reg.CONTROL_CHAR, b'\x05', b'\x10', read_mode=ReadMode.TEXT, marker=MarkerDetailsEnum.BRIEF_DETAILS),
    'ex_c_misc2': invoke_default(reg.CONTROL_CHAR, b'\x1e', b'\x1f', read_mode=ReadMode.TEXT, marker=MarkerDetailsEnum.FULL_DETAILS),
    'ex_c_null': invoke_default(reg.CONTROL_CHAR_NULL, b'\x00'),
    'ex_c_bskpc': invoke_default(reg.CONTROL_CHAR_BACKSPACE, b'\x08'),
    'ex_c_del': invoke_default(reg.CONTROL_CHAR_DELETE, b'\x7f'),
    'ex_c_esc': invoke_default(reg.CONTROL_CHAR_ESCAPE, b'\x1b'),

    'ex_p_print': invoke_default(reg.PRINTABLE_CHAR, b'a', b'b', b'c', b'd'),

    'ex_e_reset': invoke_on_escape_sequences(reg.ESCAPE_SEQ_SGR_0, seq.RESET, no_details=True),
    'ex_e_sgr': invoke_on_escape_sequences(reg.ESCAPE_SEQ_SGR, SequenceSGR(sgr.HI_BLUE), brief_details=True),
    'ex_e_sgr2': invoke_on_escape_sequences(reg.ESCAPE_SEQ_SGR, SequenceSGR(sgr.HI_YELLOW, sgr.BG_RED), brief_details=True),
    'ex_e_csi': invoke_on_escape_sequences(reg.ESCAPE_SEQ_CSI, b'\x1b\x5b\x32\x34\x64', full_details=True),
    'ex_e_nf': invoke_on_escape_sequences(reg.ESCAPE_SEQ_NF, b'\x1b\x28\x42', full_details=True),
    'ex_e_fp': invoke_on_escape_sequences(reg.ESCAPE_SEQ_FP, b'\x1b\x32', full_details=True),
    'ex_e_fe': invoke_on_escape_sequences(reg.ESCAPE_SEQ_FE, b'\x1b\x47', full_details=True),
    'ex_e_fs': invoke_on_escape_sequences(reg.ESCAPE_SEQ_FS, b'\x1b\x73', full_details=True, focus=True),

    'ex_u_1': invoke_default(reg.UTF_8_SEQ, b'\xd1', b'\x85', b'\xd0', b'\xb9'),
    'ex_u_2': invoke_on_utf8(reg.UTF_8_SEQ, '🐍'.encode('utf-8'), read_mode=ReadMode.BINARY, decode=True, print_hex=True, processed_shift=1),
    'ex_u_3': invoke_on_utf8(reg.UTF_8_SEQ, 'я ⅖ 世界'.encode('utf-8'), read_mode=ReadMode.TEXT, processed_shift=2),

    'ex_i_1': invoke_default(reg.BINARY_DATA, b'\xee', b'\xb0', b'\xc0', b'\xcc'),

    'fmt_logo11': seq.GREEN + seq.BOLD,
    'fmt_logo12': seq.COLOR_OFF,
    'fmt_logo13': seq.BLUE,
    'fmt_logo21': seq.HI_GREEN + seq.BOLD,
    'fmt_logo22': seq.GREEN,
    'fmt_logo23': seq.HI_BLUE,
    'fmt_logo31': seq.HI_GREEN + seq.BOLD,
    'fmt_logo32': seq.HI_CYAN,
    'fmt_logo33': seq.HI_MAGENTA,
    'fmt_logo41': seq.HI_GREEN + seq.BOLD,
    'fmt_logo42': seq.CYAN,
    'fmt_logo43': seq.MAGENTA,
    'fmt_logo51': seq.HI_GREEN + seq.BOLD,
    'fmt_logo52': seq.BLUE,
    'fmt_logo53': seq.BLUE,
    'fmt_ver1': seq.BLUE,
    'fmt_ver2': seq.BOLD,
    'fmt_header': seq.HI_WHITE + seq.BOLD,
    'fmt_thead': seq.DIM + seq.UNDERLINED,
    'fmt_comment': seq.GRAY,
}

with open(TPL_PATH, 'rt', encoding='utf8') as f:
    tpl = f.read()

out = processor.substitute(tpl, VARIABLES)

with open(OUTPUT_PATH, 'wt', encoding='utf8') as f:
    length = f.write(out)
    Console.info(f'Wrote {length:d} bytes to "{OUTPUT_PATH:s}"')
