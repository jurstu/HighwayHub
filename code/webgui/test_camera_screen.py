"""Original JPEG passthrough and GUI control signal tests."""

from pathlib import Path
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from camera_stuff.jpeg_frame import JpegFrame
from camera_stuff.recorder import RecordingStatus
from webgui.camera_screen import CameraScreen


class CameraScreenTests(unittest.TestCase):
    def setUp(self):
        self.screen = CameraScreen(fps=20)
        ok, data = cv2.imencode('.jpg', np.full((120, 160, 3), 80, dtype=np.uint8))
        self.assertTrue(ok)
        self.frame = JpegFrame(data.tobytes(), 160, 120)

    def test_signal_and_http_preserve_exact_original_bytes_without_codec_calls(self):
        with patch('cv2.imencode') as encode, patch('cv2.imdecode') as decode:
            self.screen.new_jpeg_signal.trigger(self.frame)
            response = self.screen.jpeg_response()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, 'image/jpeg')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertIs(response.body, self.frame.data)
        self.assertEqual(self.screen._preview[2], (160, 120))
        encode.assert_not_called()
        decode.assert_not_called()

    def test_missing_stale_and_stopped_previews_are_unavailable(self):
        self.assertEqual(self.screen.jpeg_response().status_code, 503)
        self.screen.update_jpeg(self.frame)
        received_at = self.screen._preview[0]
        with patch('webgui.camera_screen.monotonic', return_value=received_at + 3):
            self.assertEqual(self.screen.jpeg_response().status_code, 503)
        self.screen.stop()
        self.assertIsNone(self.screen._preview)

    def test_default_fps_is_30_and_invalid_rates_are_rejected(self):
        self.assertEqual(CameraScreen().fps, 30)
        for fps in [0, -1, float('inf'), float('nan')]:
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                CameraScreen(fps=fps)

    def test_controls_emit_changes_and_never_open_a_video_file(self):
        received = []
        self.screen.recording_changed_signal.addReceiver(received.append)
        self.screen.new_jpeg_signal.trigger(self.frame)
        with patch('cv2.VideoWriter') as writer:
            self.screen.set_recording(True)
            self.screen.set_recording(True)
            self.screen.set_recording(False)
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


if __name__ == '__main__':
    unittest.main()
