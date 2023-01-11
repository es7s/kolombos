# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
Module with output formatters. By default :class:`SgrRenderer` is used. It
also contains compatibility settings, see `SgrRenderer.set_up()`.

Working with non-default renderer can be achieved in two ways:

a. Method `RendererManager.set_up()` sets the default renderer globally. After that
   calling ``str(<Renderable>)`` will automatically invoke said renderer and all
   formatting will be applied.
b. Alternatively, you can use renderer's own class method `IRenderer.render()`
   directly and avoid messing up with the manager: ``HtmlRenderer.render(<Renderable>)``

.. rubric:: TL;DR

To unconditionally print formatted message to output terminal, do something like this:

>>> from pytermor import SgrRenderer, Styles, Text
>>> SgrRenderer.set_up(force_styles=True)
>>> print(Text('Warning: AAAA', Styles.WARNING))
\x1b[33mWarning: AAAA\x1b[39m


.. testsetup:: *

    from pytermor.color import Colors
    from pytermor.render import *

    SgrRenderer.set_up(force_styles=True)

-----

.. todo ::

    Scheme can be simplified, too many unnecessary abstractions for now.

    Renderable
          (implemented by Text) should include algorithms for creating intermediate
          styles for text pieces that lie in beetween first opening sequence (or tag)
          and second, for example -- this happens when one Text instance is included
          into another.
    Style's
          responsibility is to preserve the state of text piece and thats it.
    Renderer
          should transform style into corresponding output format and thats it.

    API 2:
        Text(string, style, leave_open = True)  # no style means all open styles will
        be closed at the end
        Text().append(string, style, leave_open = True)
        Text().prepend(string, style, leave_open = False)
        Text().raw
        Text().apply(style)
        Text().render(with=IRenderer())
        Text() + Text() = Text().append(Text().raw, Text().style)
        Text() + str = Text().append(str)
        str + Text() = Text().prepend(str)

        Style(style, fg, bg...)
        # no Style().render()!
        IRenderer().setup()
        IRenderer().render(text)
        SgrRenderer().is_sgr_usage_allowed()

    renderers should have instance methods only!
"""
from __future__ import annotations

import sys
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass, field
from functools import reduce
from typing import List, Sized, Any
from typing import Type, Dict, Set

from pytermor.common import LogicError
from .ansi import SequenceSGR, Span, NOOP_SEQ, Seqs, IntCodes
from .color import Color, ColorRGB, ColorIndexed16, ColorIndexed256, NOOP_COLOR, Colors
from .common import Registry
from .util.string_filter import ReplaceSGR


class Renderable(Sized, metaclass=ABCMeta):
    """
    Renderable abstract class. Can be inherited if the default style
    overlaps resolution mechanism implemented in `Text` is not good enough
    and you want to implement your own.
    """
    def render(self) -> str:
        return self._render_using(RendererManager.get_default())

    @abstractmethod
    def _render_using(self, renderer: Type[IRenderer]) -> str:
        raise NotImplemented

    def __str__(self) -> str:
        return self.render()

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplemented


class Text(Renderable):
    """
    Text
    """

    def __init__(self, text: Any = None, style: Style|str = None):
        self._runs = [self._TextRun(text, style)]

    def _render_using(self, renderer: Type[IRenderer]) -> str:
        return ''.join(run._render_using(renderer) for run in self._runs)

    def raw(self) -> str:
        return ''.join(run.raw() for run in self._runs)

    def append(self, text: str|Text):
        if isinstance(text, str):
            self._runs.append(self._TextRun(text))
        elif isinstance(text, Text):
            self._runs += text._runs
        else:
            raise TypeError('Can add Text to another Text instance or str only')

    def prepend(self, text: str|Text):
        if isinstance(text, str):
            self._runs.insert(0, self._TextRun(text))
        elif isinstance(text, Text):
            self._runs = text._runs + self._runs
        else:
            raise TypeError('Can add Text to another Text instance or str only')

    def __len__(self) -> int:
        return sum(len(r) for r in self._runs)

    def __format__(self, *args, **kwargs) -> str:
        runs_amount = len(self._runs)
        if runs_amount == 0:
            return ''.__format__(*args, **kwargs)
        if runs_amount > 1:
            raise RuntimeError(
                f'Can only __format__ Texts consisting of 0 or 1 TextRuns, '
                f'got {runs_amount}. Consider applying the styles and creating'
                f' the Text instance after value formatting.')
        return self._runs[0].__format__(*args, **kwargs)

    def __add__(self, other: str|Text) -> Text:
        self.append(other)
        return self

    def __iadd__(self, other: str|Text) -> Text:
        self.append(other)
        return self

    def __radd__(self, other: str|Text) -> Text:
        self.prepend(other)
        return self

    class _TextRun(Renderable):
        def __init__(self, string: Any = None, style: Style|str = None):
            self._string: str = str(string) if string else ''
            if isinstance(style, str):
                style = Style(fg=style)
            self._style: Style|None = style

        def _render_using(self, renderer: Type[IRenderer]) -> str:
            if not self._style:
                return self._string
            return renderer.render(self._string, self._style)

        def raw(self) -> str:
            return self._string

        def __len__(self) -> int:
            return len(self._string)

        def __format__(self, *args, **kwargs) -> str:
            self._string = self._string.__format__(*args, **kwargs)
            return self.render()


@dataclass
class Style:
    """Create a new ``Style()``.

    Key difference between ``Styles`` and ``Spans`` or ``SGRs`` is that
    ``Styles`` describe colors in RGB format and therefore support output
    rendering in several different formats (see :mod:`._render`).

    Both ``fg`` and ``bg`` can be specified as:

    1. :class:`.Color` instance or library preset;
    2. key code -- name of any of aforementioned presets, case-insensitive;
    3. integer color value in hexademical RGB format.
    4. None -- the color will be unset.

    :param fg:          Foreground (i.e., text) color.
    :param bg:          Background color.
    :param inherit:     Parent instance to copy unset properties from.
    :param blink:       Blinking effect; *supported by limited amount of Renderers*.
    :param bold:        Bold or increased intensity.
    :param crosslined:  Strikethrough.
    :param dim:         Faint, decreased intensity.
    :param double_underlined:
        Faint, decreased intensity.
    :param inversed:    Swap foreground and background colors.
    :param italic:      Italic.
    :param overlined:   Overline.
    :param underlined:  Underline.
    :param class_name:  Arbitary string used by some renderers, e.g. by ``HtmlRenderer``.

    >>> Style(fg='green', bold=True)
    Style[fg=008000, no bg, bold]
    >>> Style(bg=0x0000ff)
    Style[no fg, bg=0000ff]
    >>> Style(fg=Colors.DEEP_SKY_BLUE_1, bg=Colors.GREY_93)
    Style[fg=00afff, bg=eeeeee]
    """
    _fg: Color = field(default=None, init=False)
    _bg: Color = field(default=None, init=False)

    def __init__(self, inherit: Style = None, fg: Color|int|str = None,
                 bg: Color|int|str = None, blink: bool = None, bold: bool = None,
                 crosslined: bool = None, dim: bool = None,
                 double_underlined: bool = None, inversed: bool = None,
                 italic: bool = None, overlined: bool = None, underlined: bool = None,
                 class_name: str = None):
        if fg is not None:
            self._fg = self._resolve_color(fg, True)
        if bg is not None:
            self._bg = self._resolve_color(bg, True)

        self.blink = blink
        self.bold = bold
        self.crosslined = crosslined
        self.dim = dim
        self.double_underlined = double_underlined
        self.inversed = inversed
        self.italic = italic
        self.overlined = overlined
        self.underlined = underlined
        self.class_name = class_name

        if inherit is not None:
            self._clone_from(inherit)

        if self._fg is None:
            self._fg = NOOP_COLOR
        if self._bg is None:
            self._bg = NOOP_COLOR

    def text(self, text: Any) -> Text:
        return Text(text, self)

    def render(self, text: Any) -> str:
        return self.text(text).render()

    def autopick_fg(self) -> Style:
        """
        Pick ``fg_color`` depending on ``bg_color``. Set ``fg_color`` to
        either 4% gray (almost black) if background is bright, or to 80% gray
        (bright gray) if it is dark. If background is None, do nothing.

        .. todo ::

            check if there is a better algorithm,
            because current thinks text on #000080 should be black

        :return: self
        """
        if self._bg is None or self._bg.hex_value is None:
            return self

        h, s, v = Color.hex_value_to_hsv_channels(self._bg.hex_value)
        if v >= .45:
            self._fg = Colors.RGB_GREY_4
        else:
            self._fg = Colors.RGB_GREY_80
        return self

    def flip(self) -> Style:
        """
        Swap foreground color and background color.
        :return: self
        """
        self._fg, self._bg = self._bg, self._fg
        return self

    # noinspection PyMethodMayBeStatic
    def _resolve_color(self, arg: str|int|Color, nullable: bool) -> Color|None:
        if isinstance(arg, Color):
            return arg

        if isinstance(arg, int):
            return ColorRGB(arg)

        if isinstance(arg, str):
            resolved_color = Colors.resolve(arg)
            if not isinstance(resolved_color, Color):
                raise ValueError(f'Attribute is not valid Color: {resolved_color}')
            return resolved_color

        return None if nullable else NOOP_COLOR

    def _clone_from(self, inherit: Style):
        for attr in list(self.__dict__.keys()) + ['_fg', '_bg']:
            inherit_val = getattr(inherit, attr)
            if getattr(self, attr) is None and inherit_val is not None:
                setattr(self, attr, inherit_val)

    def __repr__(self):
        if self._fg is None or self._bg is None:
            return self.__class__.__name__ + '[uninitialized]'
        props_set = [self.fg.format_value('fg=', 'no fg'),
                     self.bg.format_value('bg=', 'no bg'), ]
        for attr_name in dir(self):
            if not attr_name.startswith('_'):
                attr = getattr(self, attr_name)
                if isinstance(attr, bool) and attr is True:
                    props_set.append(attr_name)

        return self.__class__.__name__ + '[{:s}]'.format(', '.join(props_set))

    @property
    def fg(self) -> Color:
        return self._fg

    @property
    def bg(self) -> Color:
        return self._bg

    @fg.setter
    def fg(self, val: str|int|Color):
        self._fg: Color = self._resolve_color(val, nullable=False)

    @bg.setter
    def bg(self, val: str|int|Color):
        self._bg: Color = self._resolve_color(val, nullable=False)


NOOP_STYLE = Style()
"""
Special style which passes the text 
furthrer without any modifications.
"""


class RendererManager:
    _default: Type[IRenderer] = None

    @classmethod
    def set_up(cls, default_renderer: Type[IRenderer]|None = None):
        """
        Set up renderer preferences. Affects all renderer types.

        :param default_renderer:
            Default renderer to use globally. Passing None will result in library
            default setting restored (`SgrRenderer`).

        >>> RendererManager.set_up(DebugRenderer)
        >>> Text('text', Style(fg='red')).render()
        '|ǝ31|text|ǝ39|'

        >>> NoOpRenderer.render('text',Style(fg='red'))
        'text'
        """
        cls._default = default_renderer or SgrRenderer

    @classmethod
    def get_default(cls) -> Type[IRenderer]:
        """ Get global default renderer type. """
        return cls._default


class IRenderer(metaclass=ABCMeta):
    """ Renderer interface. """

    @classmethod
    @abstractmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE) -> str:
        """
        Apply colors and attributes described in ``style`` argument to
        ``text`` and return the result. Output format depends on renderer's
        class (which defines the implementation).
        """
        raise NotImplementedError


class SgrRenderer(IRenderer):
    """
    Default renderer invoked by `Text._render()`. Transforms `Color` instances
    defined in ``style`` into ANSI control sequence bytes and merges them with
    input string.

    Respects compatibility preferences (see `RendererManager.set_up()`) and
    maps RGB colors to closest *indexed* colors if terminal doesn't support
    RGB output. In case terminal doesn't support even 256 colors, falls back
    to 16-color pallete and picks closest counterparts again the same way.

    Type of output ``SequenceSGR`` depends on type of `Color` variables in
    ``style`` argument. Keeping all that in mind, let's summarize:

    1. `ColorRGB` can be rendered as True Color sequence, 256-color sequence
       or 16-color sequence depending on compatibility settings.
    2. `ColorIndexed256` can be rendered as 256-color sequence or 16-color
       sequence.
    3. `ColorIndexed16` can be rendered as 16-color sequence.
    4. Nothing of the above will happen and all Colors will be discarded
       completely if output is not a terminal emulator or if the developer
       explicitly set up the renderer to do so (**force_styles** = False).

    >>> SgrRenderer.render('text', Style(fg='red', bold=True))
    '\\x1b[1;31mtext\\x1b[22;39m'
    """
    _force_styles: bool|None = False
    _compatibility_256_colors: bool = False
    _compatibility_16_colors: bool = False

    @classmethod
    def set_up(cls, force_styles: bool|None = False,
               compatibility_256_colors: bool = False,
               compatibility_16_colors: bool = False):
        """
        Set up renderer preferences. Affects all renderer types.

        .. todo ::
            Rewrite this part. Default should be *256* OR *RGB* if COLORTERM is either
            ``truecolor`` or ``24bit``. `setup()` overrides this, of course.

        :param force_styles:

            * If set to *None*, all renderers will pass input text through themselves
              without any changes (i.e. no colors and attributes will be applied).
            * If set to *True*, renderers will always apply the formatting regardless
              of other internal rules and algorithms.
            * If set to *False* [default], the final decision will be made
              by every renderer independently, based on their own algorithms.

        :param compatibility_256_colors:

            Disable *RGB* (or True Color) output mode. *256-color* sequences will
            be printed out instead of disabled ones. Useful when combined with
            ``curses`` -- that way you can check the terminal capabilities from the
            inside of that terminal and switch to different output mode at once.

        :param compatibility_16_colors:

            Disable *256-color* output mode and default *16-color* sequences instead.
            If this setting is set to *True*, the value of ``compatibility_256_colors``
            will be ignored completely.

        """
        cls._force_styles = force_styles
        cls._compatibility_256_colors = compatibility_256_colors
        cls._compatibility_16_colors = compatibility_16_colors

    @classmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE):
        opening_seq = cls._render_attributes(style, squash=True) + \
                      cls._render_color(style.fg, False) + \
                      cls._render_color(style.bg, True)

        # in case there are line breaks -- split text to lines and apply
        # SGRs for each line separately. it increases the chances that style
        # will be correctly displayed regardless of implementation details of
        # user's pager, multiplexer, terminal emulator etc.
        rendered_text = ''
        for line in str(text).splitlines(keepends=True):
            rendered_text += Span(opening_seq).wrap(line)
        return rendered_text

    @classmethod
    def _render_attributes(cls, style: Style, squash: bool) -> List[SequenceSGR]|SequenceSGR:
        if not cls.is_sgr_usage_allowed():
            return NOOP_SEQ if squash else [NOOP_SEQ]

        result = []
        if style.blink:             result += [Seqs.BLINK_SLOW]
        if style.bold:              result += [Seqs.BOLD]
        if style.crosslined:        result += [Seqs.CROSSLINED]
        if style.dim:               result += [Seqs.DIM]
        if style.double_underlined: result += [Seqs.DOUBLE_UNDERLINED]
        if style.inversed:          result += [Seqs.INVERSED]
        if style.italic:            result += [Seqs.ITALIC]
        if style.overlined:         result += [Seqs.OVERLINED]
        if style.underlined:        result += [Seqs.UNDERLINED]

        if squash:
            return reduce(lambda p, c: p + c, result, NOOP_SEQ)
        return result

    @classmethod
    def _render_color(cls, color: Color, bg: bool) -> SequenceSGR:
        hex_value = color.hex_value

        if not cls.is_sgr_usage_allowed() or hex_value is None:
            return NOOP_SEQ

        if isinstance(color, ColorRGB):
            if cls._compatibility_16_colors:
                return ColorIndexed16.find_closest(hex_value).to_sgr(bg=bg)
            if cls._compatibility_256_colors:
                return ColorIndexed256.find_closest(hex_value).to_sgr(bg=bg)
            return color.to_sgr(bg=bg)

        elif isinstance(color, ColorIndexed256):
            if cls._compatibility_16_colors:
                return ColorIndexed16.find_closest(hex_value).to_sgr(bg=bg)
            return color.to_sgr(bg=bg)

        elif isinstance(color, ColorIndexed16):
            return color.to_sgr(bg=bg)

        raise NotImplementedError(f'Unknown Color inhertior {color!s}')

    @classmethod
    def is_sgr_usage_allowed(cls) -> bool:
        if cls._force_styles is True:
            return True
        if cls._force_styles is None:
            return False
        return sys.stdout.isatty()


class TmuxRenderer(SgrRenderer):
    """
    tmux
    """

    SGR_TO_TMUX_MAP = {
        NOOP_SEQ:           '',
        Seqs.RESET:         'default',

        Seqs.BOLD:          'bold',
        Seqs.DIM:           'dim',
        Seqs.ITALIC:        'italics',
        Seqs.UNDERLINED:    'underscore',
        Seqs.BLINK_SLOW:    'blink',
        Seqs.BLINK_FAST:    'blink',
        Seqs.BLINK_DEFAULT: 'blink',
        Seqs.INVERSED:      'reverse',
        Seqs.HIDDEN:        'hidden',
        Seqs.CROSSLINED:    'strikethrough',
        Seqs.DOUBLE_UNDERLINED: 'double-underscore',
        Seqs.OVERLINED:     'overline',

        Seqs.BOLD_DIM_OFF:   'nobold nodim',
        Seqs.ITALIC_OFF:     'noitalics',
        Seqs.UNDERLINED_OFF: 'nounderscore',
        Seqs.BLINK_OFF:      'noblink',
        Seqs.INVERSED_OFF:   'noreverse',
        Seqs.HIDDEN_OFF:     'nohidden',
        Seqs.CROSSLINED_OFF: 'nostrikethrough',
        Seqs.OVERLINED_OFF:  'nooverline',

        Seqs.BLACK:     'fg=black',
        Seqs.RED:       'fg=red',
        Seqs.GREEN:     'fg=green',
        Seqs.YELLOW:    'fg=yellow',
        Seqs.BLUE:      'fg=blue',
        Seqs.MAGENTA:   'fg=magenta',
        Seqs.CYAN:      'fg=cyan',
        Seqs.WHITE:     'fg=white',
        Seqs.COLOR_OFF: 'fg=default',

        Seqs.BG_BLACK:     'bg=black',
        Seqs.BG_RED:       'bg=red',
        Seqs.BG_GREEN:     'bg=green',
        Seqs.BG_YELLOW:    'bg=yellow',
        Seqs.BG_BLUE:      'bg=blue',
        Seqs.BG_MAGENTA:   'bg=magenta',
        Seqs.BG_CYAN:      'bg=cyan',
        Seqs.BG_WHITE:     'bg=white',
        Seqs.BG_COLOR_OFF: 'bg=default',

        Seqs.GRAY:       'fg=brightblack',
        Seqs.HI_RED:     'fg=brightred',
        Seqs.HI_GREEN:   'fg=brightgreen',
        Seqs.HI_YELLOW:  'fg=brightyellow',
        Seqs.HI_BLUE:    'fg=brightblue',
        Seqs.HI_MAGENTA: 'fg=brightmagenta',
        Seqs.HI_CYAN:    'fg=brightcyan',
        Seqs.HI_WHITE:   'fg=brightwhite',

        Seqs.BG_GRAY:       'bg=brightblack',
        Seqs.BG_HI_RED:     'bg=brightred',
        Seqs.BG_HI_GREEN:   'bg=brightgreen',
        Seqs.BG_HI_YELLOW:  'bg=brightyellow',
        Seqs.BG_HI_BLUE:    'bg=brightblue',
        Seqs.BG_HI_MAGENTA: 'bg=brightmagenta',
        Seqs.BG_HI_CYAN:    'bg=brightcyan',
        Seqs.BG_HI_WHITE:   'bg=brightwhite',
    }

    @classmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE):
        opening_sgrs = [
            *cls._render_attributes(style, False),
            cls._render_color(style.fg, False),
            cls._render_color(style.bg, True),
        ]
        opening_tmux_style = cls._sgr_to_tmux_style(*opening_sgrs)
        closing_tmux_style = ''.join(
            cls._sgr_to_tmux_style(Span(sgr).closing_seq) for sgr in opening_sgrs
        )

        rendered_text = ''
        for line in str(text).splitlines(keepends=True):
            rendered_text += opening_tmux_style + line + closing_tmux_style
        return rendered_text

    @classmethod
    def _sgr_to_tmux_style(cls, *sgrs: SequenceSGR) -> str:
        result = ''
        for sgr in sgrs:
            if sgr.is_color_extended:
                target = 'fg'
                if sgr.params[0] == IntCodes.BG_COLOR_EXTENDED:
                    target = 'bg'

                if sgr.params[1] == IntCodes.EXTENDED_MODE_256:
                    color = 'color{}'.format(sgr.params[2])
                elif sgr.params[1] == IntCodes.EXTENDED_MODE_RGB:
                    color = '#{:06x}'.format(
                        ColorRGB.rgb_channels_to_hex_value(*sgr.params[2:])
                    )
                else:
                    raise ValueError(f"Unknown SGR param #2 (idx 1): {sgr!r}")

                result += f'#[{target}={color}]'
                continue

            tmux_style_decl = cls.SGR_TO_TMUX_MAP.get(sgr)
            if tmux_style_decl is None:
                raise LogicError(f'No tmux definiton is present for {sgr!r}')
            if len(tmux_style_decl) > 0:
                result += f'#[{tmux_style_decl}]'
        return result


class NoOpRenderer(IRenderer):
    """
    Special renderer type that does nothing with the input string and just
    returns it as is. That's true only when it _is_ a str beforehand;
    otherwise argument will be casted to str and then returned.

    >>> NoOpRenderer.render('text', Style(fg='red', bold=True))
    'text'
    """

    @classmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE) -> str:
        return str(text)


class HtmlRenderer(IRenderer):
    """
    html

    >>> HtmlRenderer.render('text',Style(fg='red', bold=True))
    '<span style="color: #800000; font-weight: 700">text</span>'
    """

    DEFAULT_ATTRS = ['color', 'background-color', 'font-weight', 'font-style',
                     'text-decoration', 'border', 'filter', ]

    @classmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE) -> str:
        span_styles: Dict[str, Set[str]] = dict()
        for attr in cls._get_default_attrs():
            span_styles[attr] = set()

        if style.fg.hex_value is not None:
            span_styles['color'].add(style.fg.format_value("#"))
        if style.bg.hex_value is not None:
            span_styles['background-color'].add(style.bg.format_value("#"))

        if style.blink:  # modern browsers doesn't support it without shit piled up
            span_styles['border'].update(('1px', 'dotted'))
        if style.bold:
            span_styles['font-weight'].add('700')
        if style.crosslined:
            span_styles['text-decoration'].add('line-through')
        if style.dim:
            span_styles['filter'].update(('saturate(0.5)', 'brightness(0.75)'))
        if style.double_underlined:
            span_styles['text-decoration'].update(('underline', 'double'))
        if style.inversed:
            span_styles['color'], span_styles['background-color'] = \
                span_styles['background-color'], span_styles['color']
        if style.italic:
            span_styles['font-style'].add('italic')
        if style.overlined:
            span_styles['text-decoration'].add('overline')
        if style.underlined:
            span_styles['text-decoration'].add('underline')

        span_class_str = '' if style.class_name is None else f' class="{style.class_name}"'
        span_style_str = '; '.join(f"{k}: {' '.join(v)}"
                                   for k, v in span_styles.items()
                                   if len(v) > 0)
        return f'<span{span_class_str} style="{span_style_str}">'+str(text)+'</span>'  # @TODO  # attribues

    @classmethod
    def _get_default_attrs(cls) -> List[str]:
        return cls.DEFAULT_ATTRS


class DebugRenderer(SgrRenderer):
    """
    DebugRenderer

    >>> DebugRenderer.render('text',Style(fg='red', bold=True))
    '|ǝ1;31|text|ǝ22;39|'
    """

    @classmethod
    def render(cls, text: Any, style: Style = NOOP_STYLE) -> str:
        return ReplaceSGR(r'|ǝ\3|').apply(super().render(str(text), style))

    @classmethod
    def is_sgr_usage_allowed(cls) -> bool:
        return True


RendererManager.set_up()


class Styles(Registry[Style]):
    """
    Some ready-to-use styles. Can be used as examples.

    This registry has unique keys in comparsion with other ones (`Seqs` / `Spans` /
    `IntCodes`),
    Therefore there is no risk of key/value duplication and all presets can be listed
    in the initial place -- at API docs page directly.
    """

    WARNING = Style(fg=Colors.YELLOW)
    WARNING_LABEL = Style(WARNING, bold=True)
    WARNING_ACCENT = Style(fg=Colors.HI_YELLOW)

    ERROR = Style(fg=Colors.RED)
    ERROR_LABEL = Style(ERROR, bold=True)
    ERROR_ACCENT = Style(fg=Colors.HI_RED)

    CRITICAL = Style(bg=Colors.HI_RED, fg=Colors.HI_WHITE)
    CRITICAL_LABEL = Style(CRITICAL, bold=True)
    CRITICAL_ACCENT = Style(CRITICAL, bold=True, blink=True)


def distribute_padded(values: List, max_len: int, pad_before: bool = False,
                      pad_after: bool = False, ) -> str:
    if pad_before:
        values.insert(0, '')
    if pad_after:
        values.append('')

    values_amount = len(values)
    gapes_amount = values_amount - 1
    values_len = sum(len(v) for v in values)
    spaces_amount = max_len - values_len
    if spaces_amount < gapes_amount:
        raise ValueError(f'There is not enough space for all values with padding')

    result = ''
    for value_idx, value in enumerate(values):
        gape_len = spaces_amount // (gapes_amount or 1)  # for last value
        result += value + ' ' * gape_len
        gapes_amount -= 1
        spaces_amount -= gape_len

    return result
