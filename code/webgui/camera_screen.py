"""Live JPEG preview and controls; file writing lives in CameraRecorder."""

from math import isfinite
from time import monotonic

from nicegui import ui
from starlette.responses import Response

from camera_stuff.recorder import RecordingStatus
from camera_stuff.jpeg_frame import JpegFrame
from logging_setup import get_logger
from Util import Signal
from .camera_preview import CameraPreview
from .main_screen import CSS
from .page_timer import PageTimer

logger = get_logger(__name__)
JPEG_PATH = '/camera/frame.jpg'
CAMERA_PATH = '/camera'

CAMERA_CSS = """
.camera-layout { flex: 1; min-height: 0; display: grid; gap: 16px;
  grid-template-columns: minmax(0, 1fr) 300px; }
.camera-view { position: relative; min-height: 0; overflow: hidden; border-radius: 18px;
  border: 1px solid #304248; background: #05090c; }
.camera-image { width: 100%; height: 100%; object-fit: contain; }
.camera-overlay { position: absolute; inset: 0; display: flex; align-items: center;
  justify-content: center; flex-direction: column; gap: 12px; color: #829198; }
.camera-live { position: absolute; top: 18px; left: 18px; z-index: 1; }
.camera-live.is-recording { color: #ff9595; background: #331b1b; border-color: #703030; }
.camera-controls { display: flex; flex-direction: column; gap: 16px; min-height: 0; }
.camera-controls .card { flex: 0 0 auto; gap: 14px; padding: 22px; }
.camera-title { font-size: 24px; font-weight: 800; letter-spacing: -.04em; }
.camera-note { color: #829198; font-size: 13px; line-height: 1.6; }
.camera-record { font-size: 16px; font-weight: 700; }
.camera-status { color: #c7f879; font-size: 13px; font-weight: 750; }
.camera-file { color: #a7b6b8; font-size: 12px; overflow-wrap: anywhere; }
.camera-error { color: #ff9595; font-size: 12px; }
.camera-navigation { border: 1px solid #40554b; border-radius: 10px; color: #c7f879 !important; }
.camera-topbar { flex: 0 0 auto; min-height: 46px; flex-wrap: wrap; }
.camera-topbar-actions { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 850px), (orientation: portrait) {
  .camera-layout { grid-template-columns: 1fr; grid-template-rows: minmax(200px, 1fr) auto; }
  .camera-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .camera-controls .card { padding: 16px; }
}
@media (max-width: 500px) {
  .camera-controls { grid-template-columns: 1fr; }
  .camera-details { display: none !important; }
}
"""


class CameraScreen:
    """Serve original camera JPEGs; no decoding, resizing or re-encoding.

    new_jpeg_signal receives JpegFrame packets and replaces a cached tuple.
    Recording controls emit booleans; recorder status is an immutable snapshot.
    """

    def __init__(self, *, fps: float = 30.0):
        if not isfinite(fps) or fps <= 0:
            raise ValueError('fps must be finite and positive')
        self.fps = float(fps)
        self.new_jpeg_signal = Signal('new original camera preview JPEG')
        self.new_jpeg_signal.addReceiver(self.update_jpeg)
        self.recording_changed_signal = Signal('camera recording requested')
        self.recording_requested = False
        self._recording_status = RecordingStatus()
        self._preview = None

    def update_jpeg(self, frame: JpegFrame):
        self._preview = (monotonic(), frame.data, (frame.width, frame.height))

    def set_recording(self, enabled: bool):
        enabled = bool(enabled)
        if enabled != self.recording_requested:
            self.recording_requested = enabled
            self.recording_changed_signal.trigger(enabled)

    def update_recording_status(self, status: RecordingStatus):
        self._recording_status = status
        self.recording_requested = status.requested

    def start(self):
        logger.debug('Camera preview endpoint=%s format=original JPEG passthrough', JPEG_PATH)

    def stop(self):
        self._preview = None

    def jpeg_response(self) -> Response:
        """Serve cached immutable bytes; every browser shares the original camera JPEG."""
        preview = self._preview
        headers = {'Cache-Control': 'no-store'}
        if preview is None or monotonic() - preview[0] > 2:
            return Response(status_code=503, headers={**headers, 'Retry-After': '1'})
        return Response(preview[1], media_type='image/jpeg', headers=headers)

    def spawn_gui(self):
        ui.dark_mode().enable()
        ui.add_css(CSS + CAMERA_CSS)
        with ui.element('main').classes('dashboard'):
            with ui.element('header').classes('topbar camera-topbar'):
                with ui.element('div').classes('brand'):
                    ui.label('H').classes('brand-mark')
                    with ui.element('div'):
                        ui.html('HIGHWAY<span>HUB</span>', sanitize=False).classes('brand-name')
                        ui.label('CAMERA VIEW').classes('brand-sub')
                with ui.element('div').classes('camera-topbar-actions'):
                    ui.button('Recordings', icon='video_library',
                              on_click=lambda: ui.navigate.to('/camera/recordings')) \
                        .props('flat no-caps color=light-green-4').classes('camera-navigation')
                    ui.button('Back to dashboard', icon='arrow_back',
                              on_click=lambda: ui.navigate.to('/main_navigation_screen')) \
                        .props('flat no-caps color=light-green-4').classes('camera-navigation')

            with ui.element('div').classes('camera-layout'):
                with ui.element('section').classes('camera-view'):
                    image = CameraPreview(JPEG_PATH, fps=self.fps).classes('camera-image')
                    image.set_visibility(False)
                    with ui.element('div').classes('camera-overlay') as waiting:
                        ui.icon('videocam_off', size='48px')
                        ui.label('Waiting for camera').classes('camera-title')
                        ui.label('The live view resumes automatically when frames arrive.')
                    live = ui.label('WAITING FOR CAMERA').classes('preview-pill camera-live')
                with ui.element('aside').classes('camera-controls'):
                    with ui.element('section').classes('card'):
                        ui.label('CAMERA CONTROL').classes('eyebrow')
                        ui.label('Video recording').classes('camera-title')
                        switch = ui.switch('Record video', value=self.recording_requested,
                                           on_change=lambda e: self.set_recording(e.value)) \
                            .props('color=light-green-4').classes('camera-record')
                        recording_status = ui.label('Recording off').classes('camera-status')
                        duration = ui.label('00:00').classes('metric-value')
                        ui.label('Preview stays live when recording is off.').classes('camera-note')
                        error = ui.label().classes('camera-error')
                    with ui.element('section').classes('card camera-details'):
                        ui.label('CAPTURE DETAILS').classes('eyebrow')
                        resolution = ui.label('Waiting for a frame').classes('camera-status')
                        ui.label(f'Preview / recording target: {self.fps:g} FPS').classes('camera-note')
                        ui.label('Local recordings').classes('camera-note')
                        filename = ui.label('No clips yet').classes('camera-file')
                        ui.label('Clips are saved locally on this device.').classes('camera-note')
            with ui.element('footer').classes('statusbar'):
                ui.label('HIGHWAYHUB / CAMERA')
                ui.label('LIVE JPEG · LOCAL VIDEO')

        def refresh():
            preview = self._preview
            connected = preview is not None and monotonic() - preview[0] <= 2
            image.set_visibility(connected)
            waiting.set_visibility(not connected)
            status = self._recording_status
            path = status.path
            live.set_text('REC · LIVE CAMERA' if path and connected else
                          'LIVE CAMERA' if connected else 'WAITING FOR CAMERA')
            live.classes(add='is-recording' if path else None,
                         remove=None if path else 'is-recording')
            if connected:
                resolution.set_text(f'{preview[2][0]} × {preview[2][1]}')
            switch.set_value(self.recording_requested)
            recording_status.set_text('Recording' if path else
                                      'Waiting for camera' if self.recording_requested else 'Recording off')
            seconds = max(0, int(monotonic() - status.started_at)) if path else 0
            duration.set_text(f'{seconds // 60:02d}:{seconds % 60:02d}')
            saved = path or status.last_path
            filename.set_text(saved.name if saved else 'No clips yet')
            error.set_text(status.error)

        refresh()
        PageTimer(0.25, refresh)
