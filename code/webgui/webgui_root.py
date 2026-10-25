from nicegui import ui, app
from .main_screen import MainScreen
from .camera_screen import CameraScreen, CAMERA_PATH, JPEG_PATH

import threading
from camera_stuff import CameraRecorder
from Util import Signal

class WebguiRoot:
    def __init__(
        self,
        port=8080,
        *,
        camera_fps=30.0,
        recorder: CameraRecorder | None = None,
    ):
        self.main_screen = MainScreen()
        self.camera_screen = CameraScreen(fps=camera_fps)
        self.recorder = recorder if recorder is not None else CameraRecorder(fps=camera_fps)
        self.new_camera_frame_signal = Signal('new camera frame for preview and recorder')
        self.new_camera_frame_signal.addReceiver(self.camera_screen.new_frame_signal.trigger)
        self.new_camera_frame_signal.addReceiver(self.recorder.new_frame_signal.trigger)
        self.camera_screen.recording_changed_signal.addReceiver(self.recorder.set_recording)
        self.recorder.status_signal.addReceiver(self.camera_screen.update_recording_status)
        self.camera_screen.update_recording_status(self.recorder.status)
        app.get(JPEG_PATH)(self.camera_screen.jpeg_response)
        app.on_startup(self.camera_screen.start)
        app.on_startup(self.recorder.start)
        app.on_shutdown(self.camera_screen.stop)
        app.on_shutdown(self.recorder.stop)
        self.port = port
        self.running = False

    def run(self):
        if self.running:
            return

        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()
        self.running = True

    def host(self):
        ui.run(self.root, reload=False, show=False, port=self.port)

    def root(self):
        ui.sub_pages({
                        '/': self.main_screen.spawn_gui,
                        "/main_navigation_screen": self.main_screen.spawn_gui,
                        CAMERA_PATH: self.camera_screen.spawn_gui,
                      })
