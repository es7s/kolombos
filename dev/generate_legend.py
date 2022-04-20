# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from os.path import dirname, abspath, join
from typing import List

from pytermor import seq, autof

from es7s_tpl_processor import Es7sTemplateProcessor
from kolombo.byteio import ReadMode, DisplayMode, MarkerDetailsEnum
from kolombo.byteio.segment import Segment
from kolombo.byteio.template import TemplateRegistry, Template
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


def invoke_default(t: Template, raw: bytes) -> str:
    labels = []
    hex = ''
    processed = []

    for idx, (rm, dm) in enumerate([
        (ReadMode.BINARY, DisplayMode.DEFAULT),
        (ReadMode.BINARY, DisplayMode.FOCUSED),
        (ReadMode.TEXT, DisplayMode.DEFAULT),
        (ReadMode.TEXT, DisplayMode.FOCUSED),
    ]):
        cur_raw = (raw if len(raw) == 1 else raw[idx:idx+1])
        segs = substitute_with(t, cur_raw, dm, rm, 1)

        label = t._label_stack.get(dm, rm).replace('\t', '').replace('\n', '')
        if label not in labels:
            labels.append(label)

        hex += autof(segs[0].opening_seq)(' ' + segs[0].raw.hex(" "))
        processed.append(autof(segs[0].opening_seq)(segs[0].processed))

    return format_example(' '.join(labels), hex, ' '.join(processed))


def invoke_control_chars() -> str:
    t = reg.CONTROL_CHAR
    label = t._label_stack.get()
    hex = ''.ljust(3)
    processed = []

    segs = substitute_with(t, b'\x01', DisplayMode.FOCUSED, ReadMode.BINARY, 0)
    hex += segs_to_hex(segs)
    processed.append(segs_to_processed(segs))

    hex += segs_to_hex(substitute_with(t, b'\x02', DisplayMode.DEFAULT, ReadMode.BINARY, 0))
    processed.append(segs_to_processed(substitute_with(t, b'\x02', DisplayMode.DEFAULT, ReadMode.TEXT, 1)))

    hex += segs_to_hex(substitute_with(t, b'\x03', DisplayMode.DEFAULT, ReadMode.BINARY, 0))
    processed.append(segs_to_processed(substitute_with(t, b'\x03', DisplayMode.DEFAULT, ReadMode.TEXT, 1)))

    return format_example(label, hex, ' '.join(processed))


def invoke_control_chars2() -> str:
    t = reg.CONTROL_CHAR
    hex = ''.ljust(6)
    processed = []

    hex += segs_to_hex(substitute_with(t, b'\x1e', DisplayMode.DEFAULT, ReadMode.BINARY, 0))
    processed.append(segs_to_processed(substitute_with(t, b'\x1e', DisplayMode.DEFAULT, ReadMode.TEXT, 2)))

    hex += segs_to_hex(substitute_with(t, b'\x1f', DisplayMode.DEFAULT, ReadMode.BINARY, 0))
    processed.append(segs_to_processed(substitute_with(t, b'\x1f', DisplayMode.DEFAULT, ReadMode.TEXT, 2)))

    return format_example('', hex, ' '.join(processed))


def substitute_with(t: Template, raw: bytes, display_mode: DisplayMode, read_mode: ReadMode,
                    marker_details: int) -> List[Segment]:
    app_settings.text = read_mode.is_text
    app_settings.binary = not app_settings.text
    setattr(app_settings, f'focus_{t._char_class.value}', display_mode.is_focused)
    app_settings.marker = marker_details
    t.update_settings()
    return t.substitute(None, raw)


def segs_to_hex(segs: List[Segment]) -> str:
    return ''.join(autof(seg.opening_seq)(' ' + seg.raw.hex(" ")) for seg in segs)


def segs_to_processed(segs: List[Segment]) -> str:
    return ''.join(autof(seg.opening_seq)(seg.processed) for seg in segs)


def format_example(label: str, hex: str, processed: str) -> str:
    result = f'{label:^6s}'
    result += ''.ljust(2) + hex
    result += ''.ljust(4) + processed + ''.ljust(4)
    return result


VARIABLES = {
    'ver': __version__,
    'ex_s_tab': invoke_default(reg.WHITESPACE_TAB, b'\x09').replace('\t', ''),
    'ex_s_lf': invoke_default(reg.WHITESPACE_NEWLINE, b'\x0a').replace('\n', ''),
    'ex_s_vtab': invoke_default(reg.WHITESPACE_VERT_TAB, b'\x0b'),
    'ex_s_ff': invoke_default(reg.WHITESPACE_FORM_FEED, b'\x0c'),
    'ex_s_cr': invoke_default(reg.WHITESPACE_CARR_RETURN, b'\x0d'),
    'ex_s_space': invoke_default(reg.WHITESPACE_SPACE, b'\x20'),

    'ex_c_misc': invoke_control_chars(),
    'ex_c_misc2': invoke_control_chars2(),
    'ex_c_null': invoke_default(reg.CONTROL_CHAR_NULL, b'\x00'),
    'ex_c_bskpc': invoke_default(reg.CONTROL_CHAR_BACKSPACE, b'\x08'),
    'ex_c_del': invoke_default(reg.CONTROL_CHAR_DELETE, b'\x7f'),
    'ex_c_esc': invoke_default(reg.CONTROL_CHAR_ESCAPE, b'\x1b'),

    'ex_p_print': invoke_default(reg.PRINTABLE_CHAR, b'abcd'),

    'ex_i_1': invoke_default(reg.BINARY_DATA, b'\xee\xb0\xc0\xcc'),

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
