"""Run with PYTHONPATH=code python -m unittest camera_stuff.test_recorder."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import Mock, patch
from subprocess import TimeoutExpired

import cv2
import numpy as np

from camera_stuff.recorder import CameraRecorder, MIN_FREE_BYTES
from camera_stuff.gstreamer import Gst
from camera_stuff.h264_writer import H264VideoWriter
from camera_stuff.jpeg_frame import JpegFrame


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix='highwayhub-recording-', dir='/tmp')
        self.addCleanup(self.directory.cleanup)
        self.recorder = CameraRecorder(Path(self.directory.name) / 'clips', fps=20)
        self.addCleanup(self.recorder._finish)
        self.frame = self.jpeg(160, 120)
        self.df = self.enterContext(patch('camera_stuff.recorder.run'))
        self.df.return_value.stdout = 'Filesystem Size Used Avail Use% Mounted on\n/dev/root 100G 10G 90G 10% /\n'
        self.disk = self.enterContext(patch('camera_stuff.recorder.statvfs'))
        self.disk.return_value = Mock(f_bavail=10_000_000_000, f_frsize=1)

    def jpeg(self, width, height):
        ok, data = cv2.imencode('.jpg', np.full((height, width, 3), 80, dtype=np.uint8))
        self.assertTrue(ok)
        return JpegFrame(data.tobytes(), width, height)

    def send_frame(self):
        self.recorder.new_jpeg_signal.trigger(self.frame)
        return self.recorder._latest[0]

    def test_receives_frames_while_off_without_creating_files(self):
        with patch('camera_stuff.recorder.H264VideoWriter') as writer:
            self.recorder._tick(self.send_frame())
        writer.assert_not_called()
        self.assertIs(self.recorder._latest[1], self.frame)
        self.assertFalse(self.recorder.recordings_dir.exists())

    def test_suggested_filename_does_not_create_files(self):
        path = self.recorder.suggest_path()
        self.assertEqual(path.parent, self.recorder.recordings_dir)
        self.assertTrue(path.name.startswith('camera-'))
        self.assertEqual(path.suffix, '.mp4')
        self.assertFalse(path.exists())

    def test_selected_filename_produces_playable_video(self):
        now = self.send_frame()
        path = Path(self.directory.name) / 'chosen' / 'drive.mp4'
        self.recorder.set_recording(True, path)
        for index in range(6):
            self.recorder._tick(now + index * 0.05)
            sleep(0.05)  # Feed at capture cadence; the encoder intentionally drops overload.
        self.assertEqual(self.recorder.status.path, path)
        self.assertEqual(self.recorder.active_path, path)
        self.recorder.set_recording(False)
        self.recorder._tick(now + 0.35)
        self.assertIsNone(self.recorder.status.path)
        self.assertIsNone(self.recorder.active_path)
        self.assertEqual(self.recorder.status.last_path, path)
        capture = cv2.VideoCapture(str(path))
        try:
            self.assertTrue(capture.isOpened())
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 6)
            self.assertEqual(capture.get(cv2.CAP_PROP_FPS), 20)
            ok, frame = capture.read()
            self.assertTrue(ok)
            self.assertEqual(frame.shape, (self.frame.height, self.frame.width, 3))
            codec = int(capture.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, 'little').decode()
            self.assertIn(codec.lower(), {'avc1', 'h264'})
            np.testing.assert_allclose(frame[60, 80], [80, 80, 80], atol=5)
            self.assertNotIn(self.frame.data, path.read_bytes())
        finally:
            capture.release()

    def test_existing_file_is_never_overwritten(self):
        path = Path(self.directory.name) / 'existing.mp4'
        path.write_bytes(b'existing recording')
        self.recorder.set_recording(True, path)
        with patch('camera_stuff.recorder.logger'):
            self.recorder._tick(self.send_frame())
        self.assertEqual(path.read_bytes(), b'existing recording')
        self.assertFalse(self.recorder.status.requested)
        self.assertTrue(self.recorder.status.error)

    def test_disconnection_closes_clip_and_reconnection_starts_new_one(self):
        now = self.send_frame()
        self.recorder.set_recording(True)
        self.recorder._tick(now)
        first = self.recorder.status.path
        self.recorder._tick(now + 3)
        self.assertIsNone(self.recorder.status.path)
        self.assertTrue(self.recorder.status.requested)
        self.recorder._latest = (now + 3.1, self.frame)
        self.recorder._tick(now + 3.1)
        self.assertIsNotNone(self.recorder.status.path)
        self.assertNotEqual(self.recorder.status.path, first)

    def test_resolution_change_starts_new_clip(self):
        now = self.send_frame()
        self.recorder.set_recording(True)
        self.recorder._tick(now)
        first = self.recorder.status.path
        self.recorder._latest = (now + 0.1, self.jpeg(320, 240))
        self.recorder._tick(now + 0.1)
        self.assertNotEqual(self.recorder.status.path, first)
        self.assertEqual(self.recorder._writer_size, (320, 240))

    def test_writer_failure_is_reported_and_partial_file_removed(self):
        now = self.send_frame()
        self.recorder.set_recording(True)
        with (
            patch('camera_stuff.recorder.H264VideoWriter', side_effect=OSError('Could not open the recording file')) as writer,
            patch('camera_stuff.recorder.logger'),
        ):
            self.recorder._tick(now)
        self.assertFalse(self.recorder.status.requested)
        self.assertIn('Could not open', self.recorder.status.error)
        self.assertEqual(list(self.recorder.recordings_dir.iterdir()), [])
        writer.assert_called_once()
        self.recorder.set_recording(True)
        self.recorder._tick(now + 0.05)
        self.assertEqual(self.recorder.status.error, '')

    def test_finalization_error_persists_until_next_request(self):
        self.recorder._writer = Mock()
        self.recorder._writer.close.side_effect = OSError('write failed')
        self.recorder._path = Path(self.directory.name) / 'failed.mp4'
        with patch('camera_stuff.recorder.logger'):
            self.recorder._tick(self.send_frame())
            self.recorder._tick(monotonic())
        self.assertIsNone(self.recorder._writer)
        self.assertFalse(self.recorder.status.requested)
        self.assertIn('Could not finalize', self.recorder.status.error)

    def test_status_signal_emits_transitions_not_every_frame(self):
        states = []
        self.recorder.status_signal.addReceiver(states.append)
        now = self.send_frame()
        self.recorder.set_recording(True)
        self.recorder._tick(now)
        self.recorder._tick(now + 0.05)
        self.recorder.set_recording(False)
        self.recorder._tick(now + 0.1)
        self.assertEqual(len(states), 2)
        self.assertIsNotNone(states[0].path)
        self.assertIsNone(states[1].path)

    def test_shutdown_finalizes_recording_without_new_camera_frames(self):
        self.recorder.set_recording(True)
        self.send_frame()
        self.recorder.start()
        self.addCleanup(self.recorder.stop)
        deadline = monotonic() + 1
        while self.recorder.status.path is None and monotonic() < deadline:
            sleep(0.001)
        self.assertIsNotNone(self.recorder.status.path)
        self.recorder.stop()
        self.assertIsNone(self.recorder.status.path)
        self.assertFalse(self.recorder.status.requested)
        self.assertTrue(self.recorder.status.last_path.is_file())

    def test_invalid_fps_and_filename_are_rejected(self):
        for fps in [0, -1, float('inf'), float('nan')]:
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                CameraRecorder(fps=fps)
        with self.assertRaises(ValueError):
            self.recorder.set_recording(True, 'clip.avi')
        for bitrate in [0, -1, 2_048_001, 1.5, True, float('inf'), float('nan')]:
            with self.subTest(bitrate=bitrate), self.assertRaises(ValueError):
                CameraRecorder(bitrate_kbps=bitrate)

    def test_configured_bitrate_reaches_encoder(self):
        self.recorder.bitrate_kbps = 2500
        self.recorder.set_recording(True)
        self.recorder._tick(self.send_frame())
        encoder = self.recorder._writer._pipeline.get_by_name('h264_encoder')
        self.assertEqual(encoder.get_property('bitrate'), 2500)

    def test_odd_dimensions_report_error_without_leaving_partial_clip(self):
        self.frame = self.jpeg(161, 121)
        self.recorder.set_recording(True)
        with patch('camera_stuff.recorder.logger'):
            self.recorder._tick(self.send_frame())
        self.assertFalse(self.recorder.status.requested)
        self.assertIn('even frame dimensions', self.recorder.status.error)
        self.assertEqual(list(self.recorder.recordings_dir.iterdir()), [])

    def test_slow_encoder_bounds_queue_without_blocking_writes(self):
        path = Path(self.directory.name) / 'overloaded.mp4'
        parse = Gst.parse_launch
        with patch('camera_stuff.h264_writer.Gst.parse_launch', side_effect=lambda pipeline:
                   parse(pipeline.replace('! jpegdec', '! identity sleep-time=100000 ! jpegdec'))):
            writer = H264VideoWriter(path, 30, (160, 120), bitrate_kbps=6000)
        try:
            writer.write(self.frame)
            deadline = monotonic() + 1
            while writer._source.get_property('current-level-buffers') and monotonic() < deadline:
                sleep(0.001)
            started = monotonic()
            for _ in range(30):
                writer.write(self.frame)
            self.assertLess(monotonic() - started, 0.5)
            self.assertLessEqual(writer._source.get_property('current-level-buffers'), 2)
        finally:
            writer.close()
        capture = cv2.VideoCapture(str(path))
        try:
            frames = 0
            while capture.read()[0]:
                frames += 1
            self.assertGreater(frames, 0)
            self.assertLessEqual(frames, 3)
        finally:
            capture.release()

    def test_checks_root_with_df_every_five_seconds_even_while_off(self):
        now = monotonic()
        self.recorder._tick(now)
        self.recorder._tick(now + 4.99)
        self.df.assert_called_once_with(['df', '-h', '/'], capture_output=True,
                                        text=True, check=True, timeout=1)
        self.disk.assert_called_once_with('/')
        self.recorder._tick(now + 5)
        self.assertEqual(self.df.call_count, 2)
        self.assertFalse(self.recorder.recordings_dir.exists())

    def test_low_space_finalizes_clip_and_blocks_restart_until_space_recovers(self):
        now = self.send_frame()
        self.recorder.set_recording(True)
        self.recorder._tick(now)
        path = self.recorder.status.path
        self.disk.return_value = Mock(f_bavail=MIN_FREE_BYTES - 1, f_frsize=1)
        self.recorder._latest = (now + 5, self.frame)
        with patch('camera_stuff.recorder.logger'):
            self.recorder._tick(now + 5)
        self.assertFalse(self.recorder.status.requested)
        self.assertIsNone(self.recorder.status.path)
        self.assertEqual(self.recorder.status.last_path, path)
        self.assertIn('less than 1 GB', self.recorder.status.error)
        self.recorder.set_recording(True)
        self.recorder._tick(now + 5.1)
        self.assertFalse(self.recorder.status.requested)
        self.assertEqual(len(list(self.recorder.recordings_dir.iterdir())), 1)

        capture = cv2.VideoCapture(str(path))
        try:
            self.assertTrue(capture.isOpened())
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
        finally:
            capture.release()

        self.disk.return_value = Mock(f_bavail=MIN_FREE_BYTES, f_frsize=1)
        self.recorder._latest = (now + 10, self.frame)
        self.recorder._tick(now + 10)
        self.assertFalse(self.recorder.status.requested)  # No automatic restart.
        self.assertEqual(self.recorder.status.error, '')
        self.recorder.set_recording(True)
        self.recorder._tick(now + 10.05)
        self.assertIsNotNone(self.recorder.status.path)

    def test_df_failure_disables_recording_until_successful_check(self):
        now = self.send_frame()
        self.recorder.set_recording(True)
        self.df.side_effect = TimeoutExpired(['df', '-h', '/'], 1)
        with patch('camera_stuff.recorder.logger'):
            self.recorder._tick(now)
        self.assertFalse(self.recorder.status.requested)
        self.assertIn('could not check', self.recorder.status.error)
        self.assertFalse(self.recorder.recordings_dir.exists())
        self.df.side_effect = None
        self.recorder._tick(now + 5)
        self.assertEqual(self.recorder.status.error, '')


if __name__ == '__main__':
    unittest.main()
