"""Browser-paced JPEG preview with one image request in flight per viewer."""

from nicegui.element import Element


class CameraPreview(Element, component='camera_preview.js'):
    def __init__(self, source: str, *, fps: float):
        super().__init__()
        self._props['src'] = source
        self._props['fps'] = fps
