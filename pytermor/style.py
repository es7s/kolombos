# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022-2023. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
S
"""
from __future__ import annotations

import typing as t
from dataclasses import dataclass, field

from . import cv
from .color import IColor, NOOP_COLOR, resolve_color
from .common import ArgTypeError, FT, CDT


@dataclass()
class Style:
    """
    Create new text render descriptior.

    Both ``fg`` and ``bg`` can be specified as existing `IColor` instance as well
    as plain *str* or *int* (for the details see `resolve_color()`).

        >>> Style(fg='green', bold=True)
        <Style[green,bold]>
        >>> Style(bg=0x0000ff)
        <Style[bg=0000FF]>
        >>> Style(fg='DeepSkyBlue1', bg='gray3')
        <Style[X39[00AFFF],bg=X232[080808]]>

    Attribute merging from ``fallback`` works this way:

        - If constructor argument is *not* empty (``True``, ``False``, `IColor`
          etc.), keep it as attribute value.
        - If constructor argument is empty (*None*), take the value from
          ``fallback``'s corresponding attribute.

    See `merge_fallback()` and `merge_overwrite()` methods and take the
    differences into account. The method used in the constructor is the first one.

    .. note ::
        Both empty (i.e., *None*) attributes of type `IColor` after initialization
        will be replaced with special constant `NOOP_COLOR`, which behaves like
        there was no color defined, and at the same time makes it safer to work
        with nullable color-type variables. Merge methods are aware of this and
        trear `NOOP_COLOR` as *None*.

    .. note ::
        All arguments except ``fallback``, ``fg`` and ``bg`` are *kwonly*-type args.

    :param fallback:    Copy unset attributes from speicifed fallback style.
                        See `merge_fallback()`.
    :param fg:          Foreground (i.e., text) color.
    :param bg:          Background color.
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
    :param class_name:  Arbitary string used by some _get_renderers, e.g. by
                        ``HtmlRenderer``.
    """

    _fg: IColor = field(default=None, init=False)
    _bg: IColor = field(default=None, init=False)

    renderable_attributes = frozenset(
        [
            "fg",
            "bg",
            "blink",
            "bold",
            "crosslined",
            "dim",
            "double_underlined",
            "inversed",
            "italic",
            "overlined",
            "underlined",
        ]
    )

    @property
    def _attributes(self) -> t.FrozenSet:
        return frozenset(list(self.__dict__.keys()) + ["_fg", "_bg"])

    def __init__(
        self,
        fallback: Style = None,
        fg: CDT | IColor = None,
        bg: CDT | IColor = None,
        *,
        blink: bool = None,
        bold: bool = None,
        crosslined: bool = None,
        dim: bool = None,
        double_underlined: bool = None,
        inversed: bool = None,
        italic: bool = None,
        overlined: bool = None,
        underlined: bool = None,
        class_name: str = None,
    ):
        if fg is not None:
            self._fg = self._resolve_color(fg)
        if bg is not None:
            self._bg = self._resolve_color(bg)

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

        if fallback is not None:
            self.merge_fallback(fallback)

        if self._fg is None:
            self._fg = NOOP_COLOR
        if self._bg is None:
            self._bg = NOOP_COLOR

    def autopick_fg(self) -> Style:
        """
        Pick ``fg_color`` depending on ``bg_color``. Set ``fg_color`` to
        either 3% gray (almost black) if background is bright, or to 80% gray
        (bright gray) if it is dark. If background is None, do nothing.

        .. todo ::

            check if there is a better algorithm,
            because current thinks text on #000080 should be black

        :return: self
        """
        if self._bg is None or self._bg.hex_value is None:
            return self

        h, s, v = self._bg.to_hsv()
        if v >= 0.45:
            self._fg = cv.GRAY_3
        else:
            self._fg = cv.GRAY_82
        return self

    def flip(self) -> Style:
        """
        Swap foreground color and background color.

        :return: self
        """
        self._fg, self._bg = self._bg, self._fg
        return self

    def clone(self) -> Style:
        """

        :return: self
        """
        return Style(self)

    def merge_fallback(self, fallback: Style) -> Style:
        """
        Merge current style with specified ``fallback`` `style <Style>`, following
        the rules:

            1. ``self`` attribute value is in priority, i.e. when both ``self`` and
               ``fallback`` attributes are defined, keep ``self`` value.
            2. If ``self`` attribute is *None*, take the value from ``fallback``'s
               corresponding attribute, and vice versa.
            3. If both attribute values are *None*, keep the *None*.

        All attributes corresponding to constructor arguments except ``fallback``
        are subject to merging. `NOOP_COLOR` is treated like *None* (default for `fg`
        and `bg`).

        .. code-block ::
            :caption: Merging different values in fallback mode

                     FALLBACK   BASE(SELF)   RESULT
                     +-------+   +------+   +------+
            ATTR-1   | False --Ø | True ===>| True |  BASE val is in priority
            ATTR-2   | True -----| None |-->| True |  no BASE val, taking FALLBACK val
            ATTR-3   | None  |   | True ===>| True |  BASE val is in priority
            ATTR-4   | None  |   | None |   | None |  no vals, keeping unset
                     +-------+   +------+   +------+

        .. seealso ::
            `merge_styles` for the examples.

        :param fallback: Style to merge the attributes with.
        :return: self
        """
        for attr in self.renderable_attributes:
            self_val = getattr(self, attr)
            if self_val is None or self_val == NOOP_COLOR:
                # @TODO refactor? maybe usage of NOOP instances is not as good as
                #       it seemed to be in the beginning
                fallback_val = getattr(fallback, attr)
                if fallback_val is not None and fallback_val != NOOP_COLOR:
                    setattr(self, attr, fallback_val)
        return self

    def merge_overwrite(self, overwrite: Style):
        """
        Merge current style with specified ``overwrite`` `style <Style>`, following
        the rules:

            1. ``overwrite`` attribute value is in priority, i.e. when both ``self``
               and ``overwrite`` attributes are defined, replace ``self`` value with
               ``overwrite`` one (in contrast to `merge_fallback()`, which works the
               opposite way).
            2. If ``self`` attribute is *None*, take the value from ``overwrite``'s
               corresponding attribute, and vice versa.
            3. If both attribute values are *None*, keep the *None*.

        All attributes corresponding to constructor arguments except ``fallback``
        are subject to merging. `NOOP_COLOR` is treated like *None* (default for `fg`
        and `bg`).

        .. code-block ::
            :caption: Merging different values in overwrite mode

                    BASE(SELF)  OVERWRITE    RESULT
                     +------+   +-------+   +-------+
            ATTR-1   | True ==Ø | False --->| False |  OVERWRITE val is in priority
            ATTR-2   | None |   | True ---->| True  |  OVERWRITE val is in priority
            ATTR-3   | True ====| None  |==>| True  |  no OVERWRITE val, keeping BASE val
            ATTR-4   | None |   | None  |   | None  |  no vals, keeping unset
                     +------+   +-------+   +-------+

        .. seealso ::
            `merge_styles` for the examples.

        :param overwrite:  Style to merge the attributes with.
        :return: self
        """
        for attr in self.renderable_attributes:
            overwrite_val = getattr(overwrite, attr)
            if overwrite_val is not None and overwrite_val != NOOP_COLOR:
                setattr(self, attr, overwrite_val)
        return self

    def _resolve_color(self, arg: str | int | IColor | None) -> IColor | None:
        if arg is None:
            return NOOP_COLOR
        if isinstance(arg, IColor):
            return arg
        if isinstance(arg, (str, int)):
            return resolve_color(arg)
        raise ArgTypeError(type(arg), "arg", fn=self._resolve_color)

    def __eq__(self, other: Style) -> bool:
        if not isinstance(other, Style):
            return False
        return all(
            getattr(self, attr) == getattr(other, attr) for attr in self._attributes
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}[{self.repr_attrs(False)}]>"

    def repr_attrs(self, verbose: bool) -> str:
        if self == NOOP_STYLE:
            props_set = ["NOP"]
        elif self._fg is None or self._bg is None:
            props_set = ["uninitialized"]
        else:
            props_set = []
            for attr_name in ("fg", "bg"):
                val: IColor = getattr(self, attr_name)
                if val == NOOP_COLOR:
                    continue
                props_set.append(
                    (f"{attr_name}=" if attr_name != "fg" else "")
                    + val.repr_attrs(verbose)
                )

        for attr_name in self.renderable_attributes:
            attr = getattr(self, attr_name)
            if isinstance(attr, bool) and attr is True:
                props_set.append(attr_name)
        return ",".join(props_set)

    @property
    def fg(self) -> IColor:
        return self._fg

    @property
    def bg(self) -> IColor:
        return self._bg

    @fg.setter
    def fg(self, val: str | int | IColor | None):
        self._fg: IColor = self._resolve_color(val)

    @bg.setter
    def bg(self, val: str | int | IColor | None):
        self._bg: IColor = self._resolve_color(val)


class _NoOpStyle(Style):
    def __bool__(self) -> bool:
        return False


NOOP_STYLE = _NoOpStyle()
""" Special style passing the text through without any modifications. """


class Styles:
    """
    Some ready-to-use styles. Can be used as examples.

    """

    WARNING = Style(fg=cv.YELLOW)
    """ """
    WARNING_LABEL = Style(WARNING, bold=True)
    """ """
    WARNING_ACCENT = Style(fg=cv.HI_YELLOW)
    """ """

    ERROR = Style(fg=cv.RED)
    """ """
    ERROR_LABEL = Style(ERROR, bold=True)
    """ """
    ERROR_ACCENT = Style(fg=cv.HI_RED)
    """ """

    CRITICAL = Style(bg=cv.RED_3, fg=cv.HI_WHITE)
    """ """
    CRITICAL_LABEL = Style(CRITICAL, bold=True)
    """ """
    CRITICAL_ACCENT = Style(CRITICAL_LABEL, blink=True)
    """ """


def make_style(fmt: FT = None) -> Style:
    """
    General `Style` constructor. Accepts a variety of argument types:

        - `CDT` (*str* or *int*)
            This argument type implies the creation of basic `Style` with
            the only attribute set being `fg` (i.e., text color). For the
            details on color resolving see `resolve_color()`.

        - `Style`
            Existing style instance. Return it as is.

        - *None*
            Return `NOOP_STYLE`.

    :param FT fmt: See `FT`.
    """
    if fmt is None:
        return NOOP_STYLE
    if isinstance(fmt, Style):
        return fmt
    if isinstance(fmt, (str, int, IColor)):
        return Style(fg=fmt)
    raise ArgTypeError(type(fmt), "fmt", fn=make_style)


def merge_styles(
    base: Style = NOOP_STYLE,
    *,
    fallbacks: t.Iterable[Style] = (),
    overwrites: t.Iterable[Style] = (),
) -> Style:
    """
    Bulk style merging method. First merge `fallbacks` `styles <Style>` with the
    ``base`` in the same order they are iterated, using `merge_fallback()` algorithm;
    then do the same for `overwrites` styles, but using `merge_overwrite()` merge
    method. The original `base` is left untouched, as all the operations are performed on
    its clone.

    .. code-block ::
       :caption: Dual mode merge diagram

                                       +-----+                                 +-----+
          >---->---->----->---->------->     >-------(B)-update---------------->     |
          |    |    |     |    |       |     |                                 |  R  |
          |    |    |     |    |       |  B  >=>Ø    [0]>-[1]>-[2]> .. -[n]>   |  E  |
       [0]>-[1]>-[2]>- .. >-[n]>->Ø    |  A  >=>Ø       |    |    |        |   |  S  |
          |    |    >- .. ------->Ø    |  S  >=>Ø       >---(D)-update----->--->  U  |
          |    >-----  .. ------->Ø    |  E  | (C) drop                        |  L  |
          >----------  .. ------->Ø    |     |=================(E)=keep========>  T  |
                                (A)    |     |                                 |     |
                  FALLBACKS    drop    +-----+            OVERWRITES           +-----+

    The key actions are marked with (**A**) to (**E**) letters. In reality the algorithm
    works in slightly different order, but the exact scheme would be less illustrative.

    :(A),(B):
        Iterate ``fallback`` styles one by one; discard all the attributes of a
        current ``fallback`` style, that are already set in ``base`` style
        (i.e., that are not *Nones*). Update all ``base`` style empty attributes
        with corresponding ``fallback`` values, if they exist and are not empty.
        Repeat these steps for the next ``fallback`` in the list, until the list
        is empty.

        .. code-block :: python
            :caption: Fallback merge algorithm example

            >>> base = Style(fg='red')
            >>> fallbacks = [Style(fg='blue'), Style(bold=True), Style(bold=False)]
            >>> merge_styles(base, fallbacks=fallbacks)
            <Style[red,bold]>

        In the example above:

            - the first fallback will be ignored, as `fg` is already set;
            - the second fallback will be applied (``base`` style will now have `bold`
              set to *True*;
            - which will make the handler ignore third fallback completely; if third
              fallback was encountered earlier than the 2nd one, ``base`` `bold` attribute
              would have been set to *False*, but alas.

    :(C),(D),(E):
        Iterate ``overwrite`` styles one by one; discard all the attributes of a ``base``
        style that have a non-empty counterpart in ``overwrite`` style, and put
        corresponding ``overwrite`` attribute values instead of them. Keep ``base``
        attribute values that have no counterpart in current ``overwrite`` style (i.e.,
        if attribute value is *None*). Then pick next ``overwrite`` style from the input
        list and repeat all these steps.

        .. code-block :: python
            :caption: Overwrite merge algorithm example

            >>> base = Style(fg='red')
            >>> overwrites = [Style(fg='blue'), Style(bold=True), Style(bold=False)]
            >>> merge_styles(base, overwrites=overwrites)
            <Style[blue]>

        In the example above all the ``overwrites`` will be applied in order they were
        put into *list*, and the result attribute values are equal to the last
        encountered non-empty values in ``overwrites`` list.

    :param base:       Basis style instance.
    :param fallbacks:  List of styles to be used as a backup attribute storage, when
                       there is no value set for the attribute in question. Uses
                       `merge_fallback()` merging strategy.
    :param overwrites: List of styles to be used as attribute storage force override
                       regardless of actual `base` attribute valuse.
    :return:           Clone of ``base`` style with all specified styles merged into.
    """
    result = base.clone()
    for fallback in fallbacks:
        result.merge_fallback(fallback)
    for overwrite in overwrites:
        result.merge_overwrite(overwrite)
    return result
