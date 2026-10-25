"""Avoid entering a removed page's slot when a NiceGUI timer starts late."""

from contextlib import nullcontext

from nicegui import ui


class PageTimer(ui.timer):
    def _get_context(self):
        return nullcontext() if self.is_deleted else super()._get_context()
