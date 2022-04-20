# -----------------------------------------------------------------------------
# es7s/kolombo [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
# @TODO make common and transfer to pytermor?
from __future__ import annotations

import re
from re import Match
from typing import Dict, Any, List

from pytermor import build, seq, StringFilter, apply_filters

from kolombo.console import Console


# noinspection PyMethodMayBeStatic
class Es7sTemplateProcessor:
    def __init__(self):
        self._variables: Dict[str, Any] = dict()
        self._filters: List[StringFilter[str]] = [
            StringFilter[str](
                lambda s: re.sub(r'#{}(.*?){}#', '', s, flags=re.DOTALL)
            ),
            StringFilter[str](
                lambda s: re.sub(r'\^{\s*([\w;]*)\s*}', lambda m: self._resolve_fmt_match(m), s)
            ),
            StringFilter[str](
                lambda s: re.sub(r':{\s*(\w+)\s*}', lambda m: self._resolve_var_match(m), s)
            ),
        ]

    def substitute(self, inp: str, variables: Dict[str, Any] = None) -> str:
        if variables:
            self._variables = variables
        return apply_filters(inp, *self._filters)

    def _resolve_fmt_match(self, m: Match) -> str:
        params_str = m.group(1)
        if len(params_str) == 0:
            return seq.RESET.print()
        params = [self._try_int(p) for p in params_str.split(';')]
        return build(*params).print()

    def _resolve_var_match(self, m: Match) -> str:
        var = m.group(1)
        if var not in self._variables.keys():
            Console.warn(f'Variable "{var}" is undefined')
            return m.group(0)
        return str(self._variables[var])

    def _try_int(self, p: str) -> int|str:
        if re.fullmatch(r'\d+', p):
            return int(p)
        return p
