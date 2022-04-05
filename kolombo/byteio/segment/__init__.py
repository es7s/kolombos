from __future__ import annotations

from pytermor.seq import SequenceSGR, EmptySequenceSGR


def _opt_arg(arg: SequenceSGR | None, allow_none: bool = False) -> SequenceSGR | None:
    if isinstance(arg, SequenceSGR):
        return arg
    if allow_none:
        return None
    return EmptySequenceSGR()
