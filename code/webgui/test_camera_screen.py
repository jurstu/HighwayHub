"""Run with PYTHONPATH=code python -m unittest webgui.test_camera_screen."""

from pathlib import Path
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from camera_stuff.recorder import RecordingStatus
from webgui.camera_screen import CameraScreen


class CameraScreenTests(unittest.TestCase):
    def setUp(self):
        self.screen = CameraScreen(fps=20)
        self.frame = np.full((120, 160, 3), 80, dtype=np.uint8)

    def send_frame(self, frame=None):
        self.screen.new_frame_signal.trigger(self.frame if frame is None else frame)
        return self.screen._latest[0]

    def test_signal_stores_latest_frame_without_encoding_or_copying(self):
        with patch('webgui.camera_screen.cv2.imencode') as encode:
            self.send_frame()
        self.assertIs(self.screen._latest[1], self.frame)
        self.assertIsNone(self.screen._preview)
        encode.assert_not_called()

    def test_preview_is_valid_jpeg_and_has_no_cache(self):
        self.assertEqual(self.screen.jpeg_response().status_code, 503)
        now = self.send_frame()
        self.screen._tick(now)
        response = self.screen.jpeg_response()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, 'image/jpeg')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        decoded = cv2.imdecode(np.frombuffer(response.body, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, self.frame.shape)
        self.screen._tick(now + 3)
        self.assertEqual(self.screen.jpeg_response().status_code, 503)

    def test_preview_is_scaled_and_unchanged_frames_are_not_reencoded(self):
        now = self.send_frame(np.zeros((1080, 1920, 3), dtype=np.uint8))
        self.screen._tick(now)
        first = self.screen._preview
        decoded = cv2.imdecode(np.frombuffer(first[1], dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, (540, 960, 3))
        self.screen._tick(now + 0.05)
        self.assertIs(self.screen._preview, first)
        self.send_frame()
        self.screen._tick(now + 0.11)
        self.assertIsNot(self.screen._preview, first)

    def test_default_fps_is_30_and_invalid_rates_are_rejected(self):
        self.assertEqual(CameraScreen().fps, 30)
        for fps in [0, -1, float('inf'), float('nan')]:
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                CameraScreen(fps=fps)

    def test_controls_emit_changes_and_never_open_a_video_file(self):
        received = []
        self.screen.recording_changed_signal.addReceiver(received.append)
        now = self.send_frame()
        with patch('cv2.VideoWriter') as writer:
            self.screen.set_recording(True)
            self.screen.set_recording(True)
            self.screen._tick(now)
            self.screen.set_recording(False)
            self.screen._tick(now + 0.05)
        self.assertEqual(received, [True, False])
        writer.assert_not_called()
        self.assertEqual(self.screen.jpeg_response().status_code, 200)

    def test_recorder_status_updates_ui_without_echoing_control_signal(self):
        received = []
        self.screen.recording_changed_signal.addReceiver(received.append)
        status = RecordingStatus(True, Path('/tmp/clip.avi'), started_at=5)
        self.screen.update_recording_status(status)
        self.assertIs(self.screen._recording_status, status)
        self.assertTrue(self.screen.recording_requested)
        self.screen.update_recording_status(RecordingStatus(error='disk full'))
        self.assertFalse(self.screen.recording_requested)
        self.assertEqual(received, [])

    def test_thread_start_stop_is_idempotent(self):
        self.screen.stop()
        self.screen.start()
        self.addCleanup(self.screen.stop)
        first = self.screen._thread
        self.screen.start()
        self.assertIs(self.screen._thread, first)
        self.screen.stop()
        self.screen.stop()
        self.assertFalse(first.is_alive())


if __name__ == '__main__':
    unittest.main()
