# -----------------------------------------------------------------------------
# es7s/kolombos [Escape sequences and control characters visualiser]
# (C) 2022 A. Shavykin <0.delameter@gmail.com>
# -----------------------------------------------------------------------------
from __future__ import annotations

from . import AbstractRunner, LegendRunner, VersionRunner, ByteIoRunner, DemoRunner
from ..settings import SettingsManager


class RunnerFactory:
    @staticmethod
    def create() -> AbstractRunner:
        if SettingsManager.app_settings.legend:
            return LegendRunner()
        elif SettingsManager.app_settings.version:
            return VersionRunner()
        elif SettingsManager.app_settings.demo:
            return DemoRunner()
        return ByteIoRunner()
