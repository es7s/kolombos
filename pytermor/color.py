# -----------------------------------------------------------------------------
#  pytermor [ANSI formatted terminal output toolset]
#  (c) 2022. A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
"""
.. testsetup:: *

    from pytermor.color import _ColorIndexed, Color, ColorIndexed16, ColorIndexed256, ColorRGB
"""
from __future__ import annotations

import logging
from abc import abstractmethod, ABCMeta
from typing import Dict, Tuple, TypeVar, List

from .ansi import SequenceSGR, NOOP_SEQ, IntCodes
from .common import LogicError, Registry


class Color(metaclass=ABCMeta):
    """
    Abstract superclass for other ``Colors``.
    """

    def __init__(self, hex_value: int = None):
        self._hex_value: int | None = hex_value

    @staticmethod
    def hex_value_to_hsv_channels(hex_value: int) -> Tuple[int, float, float]:
        """
        Transforms ``hex_value`` in ``0xffffff`` format into tuple of three
        numbers corresponding to *hue*, *saturation* and *value* channel values
        respectively. *Hue* is within [0, 359] range, *saturation* and *value* are
        within [0; 1] range.
        """
        if not isinstance(hex_value, int):
            raise TypeError(f"Argument type should be 'int', got: {type(hex_value)}")

        # https://en.wikipedia.org/wiki/HSL_and_HSV#From_RGB
        r, g, b = Color.hex_value_to_rgb_channels(hex_value)
        rn, gn, bn = r/255, g/255, b/255

        vmax = max(rn, gn, bn)
        vmin = min(rn, gn, bn)
        c = vmax - vmin
        v = vmax

        if c == 0:
            h = 0
        elif v == rn:
            h = 60 * (0 + (gn - bn)/c)
        elif v == gn:
            h = 60 * (2 + (bn - rn)/c)
        elif v == bn:
            h = 60 * (4 + (rn - gn)/c)
        else:
            raise LogicError('Impossible if-branch, algorithm is implemented '
                             'incorrectly')

        if v == 0:
            s = 0
        else:
            s = c/v

        if h < 0:
            h += 360

        return h, s, v

    @staticmethod
    def rgb_channels_to_hex_value(r: int, g: int, b: int) -> int:
        """
        .. todo ::

        :param r:
        :param g:
        :param b:
        :return:
        """
        return (r << 16) + (g << 8) + b

    @staticmethod
    def hex_value_to_rgb_channels(hex_value: int) -> Tuple[int, int, int]:
        """
        Transforms ``hex_value`` in ``0xffffff`` format into tuple of three
        integers corresponding to *red*, *blue* and *green* channel value
        respectively. Values are within [0; 255] range.

        >>> Color.hex_value_to_rgb_channels(0x80ff80)
        (128, 255, 128)
        >>> Color.hex_value_to_rgb_channels(0x000001)
        (0, 0, 1)
        """
        if not isinstance(hex_value, int):
            raise TypeError(f"Argument type should be 'int', got: {type(hex_value)}")

        return ((hex_value & 0xff0000) >> 16,
                (hex_value & 0xff00) >> 8,
                (hex_value & 0xff))

    @abstractmethod
    def to_sgr(self, bg: bool = False) -> SequenceSGR:
        raise NotImplementedError

    @property
    def hex_value(self) -> int | None:
        return self._hex_value

    def format_value(self, prefix: str|None = '0x', noop_label: str = '~') -> str:
        if self._hex_value is None:
            return noop_label
        return f'{prefix or "":s}{self._hex_value:06x}'


TypeColor = TypeVar('TypeColor', 'ColorIndexed16', 'ColorIndexed256', 'ColorRGB')
""" Any non-abstract `Color` type. """


class _ColorIndexed(Color, metaclass=ABCMeta):
    _approximator: Approximator = None

    def __init__(self, hex_value: int = None):
        super().__init__(hex_value)

        if not self.__class__._approximator:
            self.__class__._approximator = Approximator()
        self.__class__._approximator.add_to_map(self)

    @classmethod
    def find_closest(cls, hex_value: int) -> _ColorIndexed:
        """
        Wrapper for `Approximator.find_closest()`.

        :param hex_value: Integer color value in ``0xffffff`` format.
        :return:          Nearest found `_ColorIndexed` instance.

        >>> _ColorIndexed.find_closest(0xd9dbdb)
        _ColorIndexed[code=253, 0xdadada]
        """
        return cls._approximator.find_closest(hex_value)


class ColorIndexed16(_ColorIndexed):
    def __init__(self, hex_value: int = None, code_fg: int = None, code_bg: int = None):
        self._code_fg = code_fg
        self._code_bg = code_bg
        super().__init__(hex_value)
        
    def to_sgr(self, bg: bool = False) -> SequenceSGR:
        if bg:
            return SequenceSGR(self._code_bg)
        return SequenceSGR(self._code_fg)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return (self._hex_value == other._hex_value
                and self._code_bg == other._code_bg
                and self._code_fg == other._code_fg)

    def __repr__(self):
        return f'{self.__class__.__name__}[' \
               f'fg={self._code_fg!r}, ' \
               f'bg={self._code_bg!r}, ' \
               f'{self.format_value()}]'
    

class ColorIndexed256(_ColorIndexed):
    """ .. todo :: get color by int code """
    _code_map: Dict[int, ColorIndexed256] = dict()
    
    def __init__(self, hex_value: int = None, code: int = None):
        self._code = code
        super().__init__(hex_value)

        if not self._code_map.get(self._code):
            self._code_map[self._code] = self
        else:
            logging.warning(f'Indexed color duplicate by code {self._code} '
                            f'detected: {self}. It was NOT added to the index.')

    def to_sgr(self, bg: bool = False) -> SequenceSGR:
        if self._hex_value is None:
            return NOOP_SEQ
        return SequenceSGR.init_color_indexed(self._code, bg=bg)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return (self._hex_value == other._hex_value
                and self._code == other._code)

    def __repr__(self):
        return f'{self.__class__.__name__}[' \
               f'code={self._code}, ' \
               f'{self.format_value()}]'


class ColorRGB(Color):
    def to_sgr(self, bg: bool = False) -> SequenceSGR:
        if self._hex_value is None:
            return NOOP_SEQ
        return SequenceSGR.init_color_rgb(
            *self.hex_value_to_rgb_channels(self._hex_value), bg=bg)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._hex_value == other._hex_value

    def __repr__(self):
        return f'{self.__class__.__name__}[{self.format_value()}]'


class Approximator:
    """
    Internal class containing a dictionary of registred `colors <_ColorIndexed>` indexed
    by hex code along with cached nearest color search results to avoid unnecessary
    instance copies and search repeats.
    """

    def __init__(self):
        """
        Called in `Color`-type class constructors. Each `Color` type should have
        class variable with instance of `Approximator` and create it by itself if it's
        not present.
        """
        self._lookup_table: Dict[int, _ColorIndexed] = dict()
        self._approximation_cache: Dict[int, _ColorIndexed] = dict()

    def add_to_map(self, color: _ColorIndexed):
        """
        Called from `_ColorIndexed` constructors. Add a new element in color
        lookup table if it wasn't there, and then drop cached search results
        as they are most probably useless after registering a new color (i.e.
        now there will be better result for at least one cached value).

        :param color: `Color` instance being created.
        """
        if color.hex_value is None:
            return

        if color.hex_value not in self._lookup_table.keys():
            self._approximation_cache.clear()
            self._lookup_table[color.hex_value] = color

    def find_closest(self, hex_value: int) -> _ColorIndexed:
        """
        Search for nearest to ``hex_value`` registered color. Is used by
        `SgrRenderer` to find supported color alternatives in case user's terminal is
        incapable of operating in better mode.

        :param hex_value: Color value in RGB format.
        :return:          Nearest to ``hex_value`` registered ``_ColorIndexed``.
                          If no colors of required type were created (table and cache
                          are empty), ``NOOP_COLOR`` is returned.
        """
        if hex_value in self._approximation_cache.keys():
            return self._approximation_cache.get(hex_value)

        if len(self._approximation_cache) == 0:  # there was on-addition cache reset
            self._approximation_cache = self._lookup_table.copy()

        if len(self._approximation_cache) == 0:
            # rare case when `find_closest` classmethod is called from `Color` type
            # without registered instances, but it's still possible (for example,
            # developer can interrupt preset creation or just comment it out)
            logging.warning('Approximation cache is empty')
            return NOOP_COLOR_INDEXED

        closest = self.approximate(hex_value)[0]
        self._approximation_cache[hex_value] = closest
        return closest

    def approximate(self, hex_value: int, max_results: int = 1) -> List[_ColorIndexed]:
        """
        Core color approximation method. Iterate the registred colors table, or
        *lookup table*, and compute the euclidean distance from argument to each
        color of the palette. Sort the results and return the first
        ``<max_results>`` of them.

        .. note::
            It's not guaranteed that this method will **always** succeed in
            searching (the result list can be empty). Consider using `find_closest`
            instead, if you really want to be sure that at least some color will
            be returned. Another option is to use special "color" named `NOOP_COLOR`.

        .. todo :: rewrite using HSV distance?

        :param hex_value:   Color RGB value.
        :param max_results: Maximum amount of values to return.
        :return:            Closest `_ColorIndexed` instances found, sorted by color
                            distance descending (i.e. 0th element is always the
                            closest to the input value).
        """
        input_r, input_g, input_b = Color.hex_value_to_rgb_channels(hex_value)
        result: List[Tuple[_ColorIndexed, float]] = list()

        for cached_hex, cached_color in self._lookup_table.items():
            # sRGB euclidean distance
            # https://en.wikipedia.org/wiki/Color_difference#sRGB
            # https://stackoverflow.com/a/35114586/5834973
            map_r, map_g, map_b = Color.hex_value_to_rgb_channels(cached_hex)
            distance_sq = (pow(map_r - input_r, 2) +
                           pow(map_g - input_g, 2) +
                           pow(map_b - input_b, 2))

            result.append((cached_color, distance_sq))

        if len(result) == 0:
            # normally it's impossible to get here; this exception almost
            # certainly means that there is a bug somewhere in this class.
            raise LogicError(f'There are '  # pragma: no cover
                             f'no registred _ColorIndexed instances')

        sorted_result = sorted(result, key=lambda r: r[1])
        return [c for c, _ in sorted_result[:max_results]]

    def __repr__(self):
        return f'{self.__class__.__name__}[' \
               f'lookup {len(self._lookup_table)}, ' \
               f'cached {len(self._approximation_cache)}]'


NOOP_COLOR_INDEXED = ColorIndexed16()
"""
Special instance of `ColorIndexed16` class always rendering into empty string.
"""

NOOP_COLOR = ColorRGB()
"""
Special instance of `ColorRGB` class always rendering into empty string.
"""


class Colors(Registry[TypeColor]):
    """
    Registry of colors presets (`ColorIndexed16`, `ColorIndexed256`, `ColorRGB`).

    .. attention::
       Registry constants are omitted from API doc pages to improve readability
       and avoid duplication. Summary list of all presets can be found in
       `guide.presets` section of the guide.
   """

    # ---------------------------------- GENERATED ---------------------------------

    BLACK = ColorIndexed16(0x000000, IntCodes.BLACK, IntCodes.BG_BLACK)
    RED = ColorIndexed16(0x800000, IntCodes.RED, IntCodes.BG_RED)
    GREEN = ColorIndexed16(0x008000, IntCodes.GREEN, IntCodes.BG_GREEN)
    YELLOW = ColorIndexed16(0x808000, IntCodes.YELLOW, IntCodes.BG_YELLOW)
    BLUE = ColorIndexed16(0x000080, IntCodes.BLUE, IntCodes.BG_BLUE)
    MAGENTA = ColorIndexed16(0x800080, IntCodes.MAGENTA, IntCodes.BG_MAGENTA)
    CYAN = ColorIndexed16(0x008080, IntCodes.CYAN, IntCodes.BG_CYAN)
    WHITE = ColorIndexed16(0xc0c0c0, IntCodes.WHITE, IntCodes.BG_WHITE)
    GREY = ColorIndexed16(0x808080, IntCodes.GRAY, IntCodes.BG_GRAY)
    HI_RED = ColorIndexed16(0xff0000, IntCodes.HI_RED, IntCodes.BG_HI_RED)
    HI_GREEN = ColorIndexed16(0x00ff00, IntCodes.HI_GREEN, IntCodes.BG_HI_GREEN)
    HI_YELLOW = ColorIndexed16(0xffff00, IntCodes.HI_YELLOW, IntCodes.BG_HI_YELLOW)
    HI_BLUE = ColorIndexed16(0x0000ff, IntCodes.HI_BLUE, IntCodes.BG_HI_BLUE)
    HI_MAGENTA = ColorIndexed16(0xff00ff, IntCodes.HI_MAGENTA, IntCodes.BG_HI_MAGENTA)
    HI_CYAN = ColorIndexed16(0x00ffff, IntCodes.HI_CYAN, IntCodes.BG_HI_CYAN)
    HI_WHITE = ColorIndexed16(0xffffff, IntCodes.HI_WHITE, IntCodes.BG_HI_WHITE)

    GREY_0 = ColorIndexed256(0x000000, 16)
    NAVY_BLUE = ColorIndexed256(0x00005f, 17)
    DARK_BLUE = ColorIndexed256(0x000087, 18)
    BLUE_3 = ColorIndexed256(0x0000af, 19)
    BLUE_2 = ColorIndexed256(0x0000d7, 20)  # Blue3
    BLUE_1 = ColorIndexed256(0x0000ff, 21)
    DARK_GREEN = ColorIndexed256(0x005f00, 22)
    DEEP_SKY_BLUE_7 = ColorIndexed256(0x005f5f, 23)  # DeepSkyBlue4
    DEEP_SKY_BLUE_6 = ColorIndexed256(0x005f87, 24)  # DeepSkyBlue4
    DEEP_SKY_BLUE_5 = ColorIndexed256(0x005faf, 25)  # DeepSkyBlue4
    DODGER_BLUE_3 = ColorIndexed256(0x005fd7, 26)
    DODGER_BLUE_2 = ColorIndexed256(0x005fff, 27)
    GREEN_5 = ColorIndexed256(0x008700, 28)  # Green4
    SPRING_GREEN_4 = ColorIndexed256(0x00875f, 29)
    TURQUOISE_4 = ColorIndexed256(0x008787, 30)
    DEEP_SKY_BLUE_4 = ColorIndexed256(0x0087af, 31)  # DeepSkyBlue3
    DEEP_SKY_BLUE_3 = ColorIndexed256(0x0087d7, 32)
    DODGER_BLUE_1 = ColorIndexed256(0x0087ff, 33)
    GREEN_4 = ColorIndexed256(0x00af00, 34)  # Green3
    SPRING_GREEN_5 = ColorIndexed256(0x00af5f, 35)  # SpringGreen3
    DARK_CYAN = ColorIndexed256(0x00af87, 36)
    LIGHT_SEA_GREEN = ColorIndexed256(0x00afaf, 37)
    DEEP_SKY_BLUE_2 = ColorIndexed256(0x00afd7, 38)
    DEEP_SKY_BLUE_1 = ColorIndexed256(0x00afff, 39)
    GREEN_3 = ColorIndexed256(0x00d700, 40)
    SPRING_GREEN_3 = ColorIndexed256(0x00d75f, 41)
    SPRING_GREEN_6 = ColorIndexed256(0x00d787, 42)  # SpringGreen2
    CYAN_3 = ColorIndexed256(0x00d7af, 43)
    DARK_TURQUOISE = ColorIndexed256(0x00d7d7, 44)
    TURQUOISE_2 = ColorIndexed256(0x00d7ff, 45)
    GREEN_2 = ColorIndexed256(0x00ff00, 46)  # Green1
    SPRING_GREEN_2 = ColorIndexed256(0x00ff5f, 47)
    SPRING_GREEN_1 = ColorIndexed256(0x00ff87, 48)
    MEDIUM_SPRING_GREEN = ColorIndexed256(0x00ffaf, 49)
    CYAN_2 = ColorIndexed256(0x00ffd7, 50)
    CYAN_1 = ColorIndexed256(0x00ffff, 51)
    DARK_RED_2 = ColorIndexed256(0x5f0000, 52)  # DarkRed
    DEEP_PINK_8 = ColorIndexed256(0x5f005f, 53)  # DeepPink4
    PURPLE_5 = ColorIndexed256(0x5f0087, 54)  # Purple4
    PURPLE_4 = ColorIndexed256(0x5f00af, 55)
    PURPLE_3 = ColorIndexed256(0x5f00d7, 56)
    BLUE_VIOLET = ColorIndexed256(0x5f00ff, 57)
    ORANGE_4 = ColorIndexed256(0x5f5f00, 58)
    GREY_37 = ColorIndexed256(0x5f5f5f, 59)
    MEDIUM_PURPLE_7 = ColorIndexed256(0x5f5f87, 60)  # MediumPurple4
    SLATE_BLUE_3 = ColorIndexed256(0x5f5faf, 61)
    SLATE_BLUE_2 = ColorIndexed256(0x5f5fd7, 62)  # SlateBlue3
    ROYAL_BLUE_1 = ColorIndexed256(0x5f5fff, 63)
    CHARTREUSE_6 = ColorIndexed256(0x5f8700, 64)  # Chartreuse4
    DARK_SEA_GREEN_9 = ColorIndexed256(0x5f875f, 65)  # DarkSeaGreen4
    PALE_TURQUOISE_4 = ColorIndexed256(0x5f8787, 66)
    STEEL_BLUE = ColorIndexed256(0x5f87af, 67)
    STEEL_BLUE_3 = ColorIndexed256(0x5f87d7, 68)
    CORNFLOWER_BLUE = ColorIndexed256(0x5f87ff, 69)
    CHARTREUSE_5 = ColorIndexed256(0x5faf00, 70)  # Chartreuse3
    DARK_SEA_GREEN_8 = ColorIndexed256(0x5faf5f, 71)  # DarkSeaGreen4
    CADET_BLUE_2 = ColorIndexed256(0x5faf87, 72)  # CadetBlue
    CADET_BLUE = ColorIndexed256(0x5fafaf, 73)
    SKY_BLUE_3 = ColorIndexed256(0x5fafd7, 74)
    STEEL_BLUE_2 = ColorIndexed256(0x5fafff, 75)  # SteelBlue1
    CHARTREUSE_4 = ColorIndexed256(0x5fd700, 76)  # Chartreuse3
    PALE_GREEN_4 = ColorIndexed256(0x5fd75f, 77)  # PaleGreen3
    SEA_GREEN_3 = ColorIndexed256(0x5fd787, 78)
    AQUAMARINE_3 = ColorIndexed256(0x5fd7af, 79)
    MEDIUM_TURQUOISE = ColorIndexed256(0x5fd7d7, 80)
    STEEL_BLUE_1 = ColorIndexed256(0x5fd7ff, 81)
    CHARTREUSE_2 = ColorIndexed256(0x5fff00, 82)
    SEA_GREEN_4 = ColorIndexed256(0x5fff5f, 83)  # SeaGreen2
    SEA_GREEN_2 = ColorIndexed256(0x5fff87, 84)  # SeaGreen1
    SEA_GREEN_1 = ColorIndexed256(0x5fffaf, 85)
    AQUAMARINE_2 = ColorIndexed256(0x5fffd7, 86)  # Aquamarine1
    DARK_SLATE_GRAY_2 = ColorIndexed256(0x5fffff, 87)
    DARK_RED = ColorIndexed256(0x870000, 88)
    DEEP_PINK_7 = ColorIndexed256(0x87005f, 89)  # DeepPink4
    DARK_MAGENTA_2 = ColorIndexed256(0x870087, 90)  # DarkMagenta
    DARK_MAGENTA = ColorIndexed256(0x8700af, 91)
    DARK_VIOLET_2 = ColorIndexed256(0x8700d7, 92)  # DarkViolet
    PURPLE_2 = ColorIndexed256(0x8700ff, 93)  # Purple
    ORANGE_3 = ColorIndexed256(0x875f00, 94)  # Orange4
    LIGHT_PINK_3 = ColorIndexed256(0x875f5f, 95)  # LightPink4
    PLUM_4 = ColorIndexed256(0x875f87, 96)
    MEDIUM_PURPLE_6 = ColorIndexed256(0x875faf, 97)  # MediumPurple3
    MEDIUM_PURPLE_5 = ColorIndexed256(0x875fd7, 98)  # MediumPurple3
    SLATE_BLUE_1 = ColorIndexed256(0x875fff, 99)
    YELLOW_6 = ColorIndexed256(0x878700, 100)  # Yellow4
    WHEAT_4 = ColorIndexed256(0x87875f, 101)
    GREY_53 = ColorIndexed256(0x878787, 102)
    LIGHT_SLATE_GREY = ColorIndexed256(0x8787af, 103)
    MEDIUM_PURPLE_4 = ColorIndexed256(0x8787d7, 104)  # MediumPurple
    LIGHT_SLATE_BLUE = ColorIndexed256(0x8787ff, 105)
    YELLOW_4 = ColorIndexed256(0x87af00, 106)
    DARK_OLIVE_GREEN_6 = ColorIndexed256(0x87af5f, 107)  # DarkOliveGreen3
    DARK_SEA_GREEN_7 = ColorIndexed256(0x87af87, 108)  # DarkSeaGreen
    LIGHT_SKY_BLUE_3 = ColorIndexed256(0x87afaf, 109)
    LIGHT_SKY_BLUE_2 = ColorIndexed256(0x87afd7, 110)  # LightSkyBlue3
    SKY_BLUE_2 = ColorIndexed256(0x87afff, 111)
    CHARTREUSE_3 = ColorIndexed256(0x87d700, 112)  # Chartreuse2
    DARK_OLIVE_GREEN_4 = ColorIndexed256(0x87d75f, 113)  # DarkOliveGreen3
    PALE_GREEN_3 = ColorIndexed256(0x87d787, 114)
    DARK_SEA_GREEN_5 = ColorIndexed256(0x87d7af, 115)  # DarkSeaGreen3
    DARK_SLATE_GRAY_3 = ColorIndexed256(0x87d7d7, 116)
    SKY_BLUE_1 = ColorIndexed256(0x87d7ff, 117)
    CHARTREUSE_1 = ColorIndexed256(0x87ff00, 118)
    LIGHT_GREEN_2 = ColorIndexed256(0x87ff5f, 119)  # LightGreen
    LIGHT_GREEN = ColorIndexed256(0x87ff87, 120)
    PALE_GREEN_1 = ColorIndexed256(0x87ffaf, 121)
    AQUAMARINE_1 = ColorIndexed256(0x87ffd7, 122)
    DARK_SLATE_GRAY_1 = ColorIndexed256(0x87ffff, 123)
    RED_4 = ColorIndexed256(0xaf0000, 124)  # Red3
    DEEP_PINK_6 = ColorIndexed256(0xaf005f, 125)  # DeepPink4
    MEDIUM_VIOLET_RED = ColorIndexed256(0xaf0087, 126)
    MAGENTA_6 = ColorIndexed256(0xaf00af, 127)  # Magenta3
    DARK_VIOLET = ColorIndexed256(0xaf00d7, 128)
    PURPLE = ColorIndexed256(0xaf00ff, 129)
    DARK_ORANGE_3 = ColorIndexed256(0xaf5f00, 130)
    INDIAN_RED_4 = ColorIndexed256(0xaf5f5f, 131)  # IndianRed
    HOT_PINK_5 = ColorIndexed256(0xaf5f87, 132)  # HotPink3
    MEDIUM_ORCHID_4 = ColorIndexed256(0xaf5faf, 133)  # MediumOrchid3
    MEDIUM_ORCHID_3 = ColorIndexed256(0xaf5fd7, 134)  # MediumOrchid
    MEDIUM_PURPLE_2 = ColorIndexed256(0xaf5fff, 135)
    DARK_GOLDENROD = ColorIndexed256(0xaf8700, 136)
    LIGHT_SALMON_3 = ColorIndexed256(0xaf875f, 137)
    ROSY_BROWN = ColorIndexed256(0xaf8787, 138)
    GREY_63 = ColorIndexed256(0xaf87af, 139)
    MEDIUM_PURPLE_3 = ColorIndexed256(0xaf87d7, 140)  # MediumPurple2
    MEDIUM_PURPLE_1 = ColorIndexed256(0xaf87ff, 141)
    GOLD_3 = ColorIndexed256(0xafaf00, 142)
    DARK_KHAKI = ColorIndexed256(0xafaf5f, 143)
    NAVAJO_WHITE_3 = ColorIndexed256(0xafaf87, 144)
    GREY_69 = ColorIndexed256(0xafafaf, 145)
    LIGHT_STEEL_BLUE_3 = ColorIndexed256(0xafafd7, 146)
    LIGHT_STEEL_BLUE_2 = ColorIndexed256(0xafafff, 147)  # LightSteelBlue
    YELLOW_5 = ColorIndexed256(0xafd700, 148)  # Yellow3
    DARK_OLIVE_GREEN_5 = ColorIndexed256(0xafd75f, 149)  # DarkOliveGreen3
    DARK_SEA_GREEN_6 = ColorIndexed256(0xafd787, 150)  # DarkSeaGreen3
    DARK_SEA_GREEN_4 = ColorIndexed256(0xafd7af, 151)  # DarkSeaGreen2
    LIGHT_CYAN_3 = ColorIndexed256(0xafd7d7, 152)
    LIGHT_SKY_BLUE_1 = ColorIndexed256(0xafd7ff, 153)
    GREEN_YELLOW = ColorIndexed256(0xafff00, 154)
    DARK_OLIVE_GREEN_3 = ColorIndexed256(0xafff5f, 155)  # DarkOliveGreen2
    PALE_GREEN_2 = ColorIndexed256(0xafff87, 156)  # PaleGreen1
    DARK_SEA_GREEN_3 = ColorIndexed256(0xafffaf, 157)  # DarkSeaGreen2
    DARK_SEA_GREEN_1 = ColorIndexed256(0xafffd7, 158)
    PALE_TURQUOISE_1 = ColorIndexed256(0xafffff, 159)
    RED_3 = ColorIndexed256(0xd70000, 160)
    DEEP_PINK_5 = ColorIndexed256(0xd7005f, 161)  # DeepPink3
    DEEP_PINK_3 = ColorIndexed256(0xd70087, 162)
    MAGENTA_3 = ColorIndexed256(0xd700af, 163)
    MAGENTA_5 = ColorIndexed256(0xd700d7, 164)  # Magenta3
    MAGENTA_4 = ColorIndexed256(0xd700ff, 165)  # Magenta2
    DARK_ORANGE_2 = ColorIndexed256(0xd75f00, 166)  # DarkOrange3
    INDIAN_RED_3 = ColorIndexed256(0xd75f5f, 167)  # IndianRed
    HOT_PINK_4 = ColorIndexed256(0xd75f87, 168)  # HotPink3
    HOT_PINK_3 = ColorIndexed256(0xd75faf, 169)  # HotPink2
    ORCHID_3 = ColorIndexed256(0xd75fd7, 170)  # Orchid
    MEDIUM_ORCHID_2 = ColorIndexed256(0xd75fff, 171)  # MediumOrchid1
    ORANGE_2 = ColorIndexed256(0xd78700, 172)  # Orange3
    LIGHT_SALMON_2 = ColorIndexed256(0xd7875f, 173)  # LightSalmon3
    LIGHT_PINK_2 = ColorIndexed256(0xd78787, 174)  # LightPink3
    PINK_3 = ColorIndexed256(0xd787af, 175)
    PLUM_3 = ColorIndexed256(0xd787d7, 176)
    VIOLET = ColorIndexed256(0xd787ff, 177)
    GOLD_2 = ColorIndexed256(0xd7af00, 178)  # Gold3
    LIGHT_GOLDENROD_5 = ColorIndexed256(0xd7af5f, 179)  # LightGoldenrod3
    TAN = ColorIndexed256(0xd7af87, 180)
    MISTY_ROSE_3 = ColorIndexed256(0xd7afaf, 181)
    THISTLE_3 = ColorIndexed256(0xd7afd7, 182)
    PLUM_2 = ColorIndexed256(0xd7afff, 183)
    YELLOW_3 = ColorIndexed256(0xd7d700, 184)
    KHAKI_3 = ColorIndexed256(0xd7d75f, 185)
    LIGHT_GOLDENROD_3 = ColorIndexed256(0xd7d787, 186)  # LightGoldenrod2
    LIGHT_YELLOW_3 = ColorIndexed256(0xd7d7af, 187)
    GREY_84 = ColorIndexed256(0xd7d7d7, 188)
    LIGHT_STEEL_BLUE_1 = ColorIndexed256(0xd7d7ff, 189)
    YELLOW_2 = ColorIndexed256(0xd7ff00, 190)
    DARK_OLIVE_GREEN_2 = ColorIndexed256(0xd7ff5f, 191)  # DarkOliveGreen1
    DARK_OLIVE_GREEN_1 = ColorIndexed256(0xd7ff87, 192)
    DARK_SEA_GREEN_2 = ColorIndexed256(0xd7ffaf, 193)  # DarkSeaGreen1
    HONEYDEW_2 = ColorIndexed256(0xd7ffd7, 194)
    LIGHT_CYAN_1 = ColorIndexed256(0xd7ffff, 195)
    RED_1 = ColorIndexed256(0xff0000, 196)
    DEEP_PINK_4 = ColorIndexed256(0xff005f, 197)  # DeepPink2
    DEEP_PINK_2 = ColorIndexed256(0xff0087, 198)  # DeepPink1
    DEEP_PINK_1 = ColorIndexed256(0xff00af, 199)
    MAGENTA_2 = ColorIndexed256(0xff00d7, 200)
    MAGENTA_1 = ColorIndexed256(0xff00ff, 201)
    ORANGE_RED_1 = ColorIndexed256(0xff5f00, 202)
    INDIAN_RED_1 = ColorIndexed256(0xff5f5f, 203)
    INDIAN_RED_2 = ColorIndexed256(0xff5f87, 204)  # IndianRed1
    HOT_PINK_2 = ColorIndexed256(0xff5faf, 205)  # HotPink
    HOT_PINK = ColorIndexed256(0xff5fd7, 206)
    MEDIUM_ORCHID_1 = ColorIndexed256(0xff5fff, 207)
    DARK_ORANGE = ColorIndexed256(0xff8700, 208)
    SALMON_1 = ColorIndexed256(0xff875f, 209)
    LIGHT_CORAL = ColorIndexed256(0xff8787, 210)
    PALE_VIOLET_RED_1 = ColorIndexed256(0xff87af, 211)
    ORCHID_2 = ColorIndexed256(0xff87d7, 212)
    ORCHID_1 = ColorIndexed256(0xff87ff, 213)
    ORANGE_1 = ColorIndexed256(0xffaf00, 214)
    SANDY_BROWN = ColorIndexed256(0xffaf5f, 215)
    LIGHT_SALMON_1 = ColorIndexed256(0xffaf87, 216)
    LIGHT_PINK_1 = ColorIndexed256(0xffafaf, 217)
    PINK_1 = ColorIndexed256(0xffafd7, 218)
    PLUM_1 = ColorIndexed256(0xffafff, 219)
    GOLD_1 = ColorIndexed256(0xffd700, 220)
    LIGHT_GOLDENROD_4 = ColorIndexed256(0xffd75f, 221)  # LightGoldenrod2
    LIGHT_GOLDENROD_2 = ColorIndexed256(0xffd787, 222)
    NAVAJO_WHITE_1 = ColorIndexed256(0xffd7af, 223)
    MISTY_ROSE_1 = ColorIndexed256(0xffd7d7, 224)
    THISTLE_1 = ColorIndexed256(0xffd7ff, 225)
    YELLOW_1 = ColorIndexed256(0xffff00, 226)
    LIGHT_GOLDENROD_1 = ColorIndexed256(0xffff5f, 227)
    KHAKI_1 = ColorIndexed256(0xffff87, 228)
    WHEAT_1 = ColorIndexed256(0xffffaf, 229)
    CORNSILK_1 = ColorIndexed256(0xffffd7, 230)
    GREY_100 = ColorIndexed256(0xffffff, 231)
    GREY_3 = ColorIndexed256(0x080808, 232)
    GREY_7 = ColorIndexed256(0x121212, 233)
    GREY_11 = ColorIndexed256(0x1c1c1c, 234)
    GREY_15 = ColorIndexed256(0x262626, 235)
    GREY_19 = ColorIndexed256(0x303030, 236)
    GREY_23 = ColorIndexed256(0x3a3a3a, 237)
    GREY_27 = ColorIndexed256(0x444444, 238)
    GREY_30 = ColorIndexed256(0x4e4e4e, 239)
    GREY_35 = ColorIndexed256(0x585858, 240)
    GREY_39 = ColorIndexed256(0x626262, 241)
    GREY_42 = ColorIndexed256(0x6c6c6c, 242)
    GREY_46 = ColorIndexed256(0x767676, 243)
    GREY_50 = ColorIndexed256(0x808080, 244)
    GREY_54 = ColorIndexed256(0x8a8a8a, 245)
    GREY_58 = ColorIndexed256(0x949494, 246)
    GREY_62 = ColorIndexed256(0x9e9e9e, 247)
    GREY_66 = ColorIndexed256(0xa8a8a8, 248)
    GREY_70 = ColorIndexed256(0xb2b2b2, 249)
    GREY_74 = ColorIndexed256(0xbcbcbc, 250)
    GREY_78 = ColorIndexed256(0xc6c6c6, 251)
    GREY_82 = ColorIndexed256(0xd0d0d0, 252)
    GREY_85 = ColorIndexed256(0xdadada, 253)
    GREY_89 = ColorIndexed256(0xe4e4e4, 254)
    GREY_93 = ColorIndexed256(0xeeeeee, 255)

    TRUE_BLACK = ColorRGB(0x000000)
    TRUE_WHITE = ColorRGB(0xffffff)
    RGB_GREY_1 = ColorRGB(0x020202)
    RGB_GREY_2 = ColorRGB(0x050505)
    RGB_GREY_3 = ColorRGB(0x070707)
    RGB_GREY_4 = ColorRGB(0x0a0a0a)
    RGB_GREY_5 = ColorRGB(0x0c0c0c)
    RGB_GREY_6 = ColorRGB(0x0f0f0f)
    RGB_GREY_7 = ColorRGB(0x111111)
    RGB_GREY_8 = ColorRGB(0x141414)
    RGB_GREY_9 = ColorRGB(0x171717)
    RGB_GREY_10 = ColorRGB(0x191919)
    RGB_GREY_15 = ColorRGB(0x262626)
    RGB_GREY_20 = ColorRGB(0x333333)
    RGB_GREY_25 = ColorRGB(0x404040)
    RGB_GREY_30 = ColorRGB(0x4c4c4c)
    RGB_GREY_35 = ColorRGB(0x595959)
    RGB_GREY_40 = ColorRGB(0x666666)
    RGB_GREY_45 = ColorRGB(0x737373)
    RGB_GREY_50 = ColorRGB(0x808080)
    RGB_GREY_55 = ColorRGB(0x8c8c8c)
    RGB_GREY_60 = ColorRGB(0x999999)
    RGB_GREY_65 = ColorRGB(0xa6a6a6)
    RGB_GREY_70 = ColorRGB(0xb3b3b3)
    RGB_GREY_75 = ColorRGB(0xc0c0c0)
    RGB_GREY_80 = ColorRGB(0xcccccc)
    RGB_GREY_85 = ColorRGB(0xd9d9d9)
    RGB_GREY_90 = ColorRGB(0xe6e6e6)
    RGB_GREY_91 = ColorRGB(0xe8e8e8)
    RGB_GREY_92 = ColorRGB(0xebebeb)
    RGB_GREY_93 = ColorRGB(0xeeeeee)
    RGB_GREY_94 = ColorRGB(0xf1f1f1)
    RGB_GREY_95 = ColorRGB(0xf3f3f3)
    RGB_GREY_96 = ColorRGB(0xf5f5f5)
    RGB_GREY_97 = ColorRGB(0xf8f8f8)
    RGB_GREY_98 = ColorRGB(0xfafafa)
    RGB_GREY_99 = ColorRGB(0xfdfdfd)
