"""Run with: PYTHONPATH=code python -m unittest camera_stuff.test_camera"""

import unittest
from time import monotonic, sleep
from unittest.mock import Mock, patch

import cv2
import numpy as np

from camera_stuff.camera import Camera


class CameraTests(unittest.TestCase):
    def capture(self, frame=None, *, opened=True):
        capture = Mock()
        capture.open.return_value = opened
        capture.read.return_value = (True, frame)
        capture.get.side_effect = {
            cv2.CAP_PROP_FRAME_WIDTH: 32,
            cv2.CAP_PROP_FRAME_HEIGHT: 24,
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*'MJPG'),
            cv2.CAP_PROP_BUFFERSIZE: 10,
        }.get
        capture.getBackendName.return_value = 'V4L2'
        return capture

    def wait_for(self, condition):
        deadline = monotonic() + 1
        while not condition():
            if monotonic() >= deadline:
                self.fail("camera worker did not respond")
            sleep(0.001)

    def receive_once(self, camera, captures, receiver):
        def receive(frame):
            try:
                receiver(frame)
            finally:
                camera.stop()

        camera.new_frame_signal.addReceiver(receive)
        with patch("camera_stuff.camera.cv2.VideoCapture", side_effect=captures):
            try:
                camera.start()
                self.wait_for(lambda: not camera._thread.is_alive())
            finally:
                camera.stop()

    def test_native_resolution_passes_original_frame_without_resize(self):
        frame = np.zeros((24, 32, 3), dtype=np.uint8)
        capture = self.capture(frame)
        camera = Camera(2, (32, 24), backend=cv2.CAP_V4L2)
        received = []
        with patch("camera_stuff.camera.cv2.resize") as resize:
            self.receive_once(camera, [capture], received.append)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0], frame)
        resize.assert_not_called()
        capture.open.assert_called_once_with(2, cv2.CAP_V4L2)
        capture.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, 32)
        capture.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, 24)
        capture.set.assert_any_call(cv2.CAP_PROP_FPS, 30.0)
        capture.set.assert_any_call(cv2.CAP_PROP_BUFFERSIZE, 10)
        capture.release.assert_called_once()
        self.assertIsNone(camera.frame)

    def test_requests_transport_format_before_resolution_and_fps(self):
        capture = self.capture(np.zeros((24, 32, 3), dtype=np.uint8))
        camera = Camera('/dev/video4', (32, 24), fps=25, fourcc='MJPG', buffers=2)
        with patch('camera_stuff.camera.logger') as logger:
            self.receive_once(camera, [capture], lambda frame: None)
        properties = [call.args[0] for call in capture.set.call_args_list]
        self.assertEqual(properties[:4], [cv2.CAP_PROP_FOURCC, cv2.CAP_PROP_FRAME_WIDTH,
                                          cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS])
        capture.set.assert_any_call(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        capture.set.assert_any_call(cv2.CAP_PROP_FPS, 25.0)
        capture.set.assert_any_call(cv2.CAP_PROP_BUFFERSIZE, 2)
        message, *args = logger.debug.call_args.args
        self.assertIn("endpoint='/dev/video4' backend=V4L2", message % tuple(args))
        self.assertIn('negotiated=32x24 @ 30.00 FPS format=MJPG', message % tuple(args))

    def test_logs_when_driver_keeps_slow_uncompressed_mode(self):
        capture = self.capture(np.zeros((24, 32, 3), dtype=np.uint8))
        capture.set.return_value = False  # Driver rejects the requested settings.
        capture.get.side_effect = {
            cv2.CAP_PROP_FRAME_WIDTH: 32,
            cv2.CAP_PROP_FRAME_HEIGHT: 24,
            cv2.CAP_PROP_FPS: 5.0,
            cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*'YUYV'),
            cv2.CAP_PROP_BUFFERSIZE: 10,
        }.get
        camera = Camera(resolution=(32, 24), fps=30, fourcc='MJPG')
        received = []
        with patch('camera_stuff.camera.logger') as logger:
            self.receive_once(camera, [capture], received.append)
        self.assertEqual(len(received), 1)
        messages = [call.args[0] % call.args[1:] for call in logger.warning.call_args_list]
        self.assertTrue(any('5.00 FPS below requested 30.00 FPS' in message for message in messages))
        self.assertTrue(any("'YUYV' instead of 'MJPG'" in message for message in messages))

    def test_measures_delivered_fps_instead_of_trusting_driver(self):
        capture = self.capture(np.zeros((24, 32, 3), dtype=np.uint8))
        camera = Camera(resolution=(32, 24))
        count = 0

        def receive(frame):
            nonlocal count
            count += 1
            if count == 150:
                camera.stop()

        camera.new_frame_signal.addReceiver(receive)
        camera._stopping = False
        times = [0]
        for i in range(1, 151):
            times.extend([(i - 1) / 30, i / 30 - 0.001, i / 30])
        times.append(5)
        with (
            patch('camera_stuff.camera.cv2.VideoCapture', return_value=capture),
            patch('camera_stuff.camera.monotonic', side_effect=times),
            patch('camera_stuff.camera.logger') as logger,
        ):
            camera._run()
        self.assertEqual(count, 150)
        self.assertEqual(logger.debug.call_args.args[2], 30.0)
        self.assertIn('delivered', logger.debug.call_args.args[0])
        self.assertAlmostEqual(logger.debug.call_args.args[3], 1000 / 30 - 1)
        self.assertAlmostEqual(logger.debug.call_args.args[4], 1)

    def test_unsupported_resolution_is_resized_before_signal(self):
        frame = np.zeros((12, 16, 3), dtype=np.uint8)
        capture = self.capture(frame)
        camera = Camera(resolution=(32, 24))
        received = []
        self.receive_once(camera, [capture], received.append)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].shape, (24, 32, 3))

    def test_reconnects_after_open_failure_read_failure_and_opencv_error(self):
        frame = np.zeros((24, 32, 3), dtype=np.uint8)
        unopened = self.capture(opened=False)
        disconnected = self.capture()
        disconnected.read.return_value = (False, None)
        broken = self.capture()
        broken.read.side_effect = cv2.error("disconnected")
        empty = self.capture(np.empty((0, 0, 3), dtype=np.uint8))
        restored = self.capture(frame)
        captures = [unopened, disconnected, broken, empty, restored]
        camera = Camera(resolution=(32, 24), reconnect_delay=0.001)
        received = []
        with patch("camera_stuff.camera.logger"):
            self.receive_once(camera, captures, received.append)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0], frame)
        for capture in captures:
            capture.release.assert_called_once()

    def test_stop_interrupts_long_reconnect_delay(self):
        capture = self.capture(opened=False)
        camera = Camera(reconnect_delay=60)
        with (
            patch("camera_stuff.camera.cv2.VideoCapture", return_value=capture),
            patch("camera_stuff.camera.logger"),
        ):
            try:
                camera.start()
                self.wait_for(lambda: capture.release.called)
            finally:
                camera.stop(timeout=0.5)
        self.assertFalse(camera._thread.is_alive())
        capture.open.assert_called_once()

    def test_stop_timeout_prevents_restart_until_blocked_read_returns(self):
        state = {"reading": False, "unblock": False}

        def read():
            state["reading"] = True
            while not state["unblock"]:
                sleep(0.001)
            return True, np.zeros((24, 32, 3), dtype=np.uint8)

        capture = self.capture()
        capture.read.side_effect = read
        camera = Camera(resolution=(32, 24))
        received = Mock()
        camera.new_frame_signal.addReceiver(received)
        with patch("camera_stuff.camera.cv2.VideoCapture", return_value=capture):
            try:
                camera.stop()  # Also safe before starting.
                camera.start()
                self.wait_for(lambda: state["reading"])
                thread = camera._thread
                self.assertIs(camera.start(), camera)
                self.assertIs(camera._thread, thread)
                with self.assertRaises(TimeoutError):
                    camera.stop(timeout=0.001)
                with self.assertRaises(RuntimeError):
                    camera.start()
                capture.release.assert_not_called()
            finally:
                state["unblock"] = True
                camera.stop()
        received.assert_not_called()
        capture.release.assert_called_once()
        camera.stop()  # Repeated stops are safe too.

    def test_restart_after_clean_shutdown(self):
        frame = np.zeros((24, 32, 3), dtype=np.uint8)
        captures = [self.capture(frame), self.capture(frame)]
        camera = Camera(resolution=(32, 24))
        received = []

        def receive(frame):
            received.append(frame)
            camera.stop()

        camera.new_frame_signal.addReceiver(receive)
        with patch("camera_stuff.camera.cv2.VideoCapture", side_effect=captures):
            try:
                for _ in captures:
                    camera.start()
                    self.wait_for(lambda: not camera._thread.is_alive())
            finally:
                camera.stop()
        self.assertEqual(len(received), 2)
        for capture in captures:
            capture.release.assert_called_once()

    def test_invalid_settings_fail_before_starting(self):
        for resolution in [(0, 10), (10, -1), (1.5, 10), (10,), (True, 10)]:
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                Camera(resolution=resolution)
        for delay in [0, -1, float("inf"), float("nan")]:
            with self.subTest(delay=delay), self.assertRaises(ValueError):
                Camera(reconnect_delay=delay)
        for fps in [0, -1, float('inf'), float('nan')]:
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                Camera(fps=fps)
        for fourcc in ['', 'MJPEG', '☺abc']:
            with self.subTest(fourcc=fourcc), self.assertRaises(ValueError):
                Camera(fourcc=fourcc)
        for buffers in [0, -1, 1.5, True]:
            with self.subTest(buffers=buffers), self.assertRaises(ValueError):
                Camera(buffers=buffers)


if __name__ == "__main__":
    unittest.main()
