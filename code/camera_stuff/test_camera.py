"""Real GStreamer tests using a synthetic JPEG source, without camera hardware."""

from time import monotonic, sleep
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from camera_stuff.camera import Camera
from camera_stuff.gstreamer import Gst


class CameraTests(unittest.TestCase):
    def camera(self, *, resolution=(160, 120), finite=False, **settings):
        width, height = resolution
        source = ('videotestsrc is-live=true pattern=solid-color foreground-color=0xff336699 '
                  + ('num-buffers=4 ' if finite else '')
                  + f'! video/x-raw,format=RGB,width={width},height={height},framerate=30/1 ! jpegenc')
        return Camera(resolution=resolution, source_pipeline=source, **settings)

    def run_frames(self, camera, count=8):
        frames = []

        def receive(frame):
            frames.append(frame)
            if len(frames) == count:
                camera.stop()

        camera.new_jpeg_signal.addReceiver(receive)
        try:
            camera.start()
            camera._thread.join(4)
        finally:
            camera.stop()
        self.assertEqual(len(frames), count)
        self.assertFalse(camera._thread.is_alive())
        return frames

    def test_original_jpeg_output_is_valid_without_decoded_receivers(self):
        camera = self.camera()
        frames = self.run_frames(camera)
        self.assertIsNone(camera.frame)
        self.assertIsNone(camera.jpeg)  # Cleared after shutdown.
        self.assertEqual((frames[0].width, frames[0].height), (160, 120))
        image = cv2.imdecode(np.frombuffer(frames[0].data, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(image.shape, (120, 160, 3))
        np.testing.assert_allclose(image[60, 80], [153, 102, 51], atol=5)

    def test_decoded_output_supports_padded_row_strides(self):
        camera = self.camera(resolution=(161, 121))
        decoded = []
        camera.new_frame_signal.addReceiver(decoded.append)
        self.run_frames(camera)
        self.assertTrue(decoded)
        self.assertEqual(decoded[0].shape, (121, 161, 3))
        np.testing.assert_allclose(decoded[0][60, 80], [153, 102, 51], atol=5)

    def test_reconnects_after_end_of_stream(self):
        camera = self.camera(finite=True, reconnect_delay=0.01)
        with patch('camera_stuff.camera.logger') as logger:
            self.run_frames(camera, 6)
        self.assertTrue(logger.warning.called)

    def test_reconnects_after_open_error(self):
        camera = self.camera(reconnect_delay=0.01)
        create = camera._create_pipeline
        attempts = []

        def open_pipeline():
            attempts.append(True)
            if len(attempts) == 1:
                raise OSError('device disconnected')
            return create()

        with patch.object(camera, '_create_pipeline', side_effect=open_pipeline), patch('camera_stuff.camera.logger'):
            self.run_frames(camera, 3)
        self.assertEqual(len(attempts), 2)

    def test_stop_interrupts_reconnect_wait_and_start_is_idempotent(self):
        camera = self.camera(reconnect_delay=60)
        with patch.object(camera, '_create_pipeline', side_effect=OSError('unplugged')) as create, patch('camera_stuff.camera.logger'):
            camera.stop()
            camera.start()
            try:
                self.assertIs(camera.start(), camera)
                deadline = monotonic() + 1
                while not create.called and monotonic() < deadline:
                    sleep(0.001)
                self.assertTrue(create.called)
            finally:
                camera.stop(timeout=0.5)
        self.assertFalse(camera._thread.is_alive())

    def test_restarts_after_clean_shutdown(self):
        camera = self.camera()
        frames = []
        camera.new_jpeg_signal.addReceiver(lambda frame: (frames.append(frame), camera.stop()))
        for _ in range(2):
            camera.start()
            camera._thread.join(2)
            camera.stop()
        self.assertEqual(len(frames), 2)

    def test_device_path_is_a_property_not_pipeline_text(self):
        camera = Camera('/dev/camera with spaces', (1920, 1080), fps=29.97)
        pipeline = camera._create_pipeline()
        try:
            self.assertEqual(pipeline.get_by_name('camera_source').get_property('device'), camera.source)
            self.assertIsNotNone(pipeline.get_by_name('jpeg_sink'))
            self.assertIsNotNone(pipeline.get_by_name('bgr_sink'))
        finally:
            pipeline.set_state(Gst.State.NULL)

    def test_invalid_settings_fail_before_starting(self):
        for resolution in [(0, 10), (10, -1), (1.5, 10), (10,), (True, 10)]:
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                Camera(resolution=resolution)
        for value in [0, -1, float('inf'), float('nan')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                Camera(fps=value)
            with self.assertRaises(ValueError):
                Camera(reconnect_delay=value)
        for buffers in [0, -1, 1.5, True]:
            with self.subTest(buffers=buffers), self.assertRaises(ValueError):
                Camera(buffers=buffers)


if __name__ == '__main__':
    unittest.main()
