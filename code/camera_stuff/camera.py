"""Threaded GStreamer capture: original JPEG packets and optional decoded BGR."""

from fractions import Fraction
from math import isfinite
from os.path import realpath
from threading import Thread, current_thread
from time import monotonic, sleep

import numpy as np

from logging_setup import get_logger
from Util import Signal
from .gstreamer import GLib, Gst, GstVideo, check_bus, init_gst
from .jpeg_frame import JpegFrame

logger = get_logger(__name__)


class Camera:
    """Emit JpegFrame on new_jpeg_signal and read-only BGR on new_frame_signal.

    One worker polls two appsinks; GStreamer owns the capture/decoder threads.
    The decoder branch is enabled only while new_frame_signal has receivers.
    JPEG consumers never wait for decoding. Keep signal callbacks short.
    Connect receivers before start(); control start/stop from one thread.
    source_pipeline optionally supplies a GStreamer source ending in image/jpeg
    (useful for network cameras or synthetic tests). No locks or async code.
    """

    def __init__(self, source: int | str = 0, resolution: tuple[int, int] = (1280, 720), *,
                 fps: float = 30.0, buffers: int = 10, report_fps: bool = False,
                 reconnect_delay: float = 1.0, source_pipeline: str | None = None):
        if len(resolution) != 2 or any(type(n) is not int or n <= 0 for n in resolution):
            raise ValueError('resolution must be (width, height) in positive integers')
        if not isfinite(fps) or fps <= 0:
            raise ValueError('fps must be finite and positive')
        if not isfinite(reconnect_delay) or reconnect_delay <= 0:
            raise ValueError('reconnect_delay must be finite and positive')
        if type(buffers) is not int or buffers < 1:
            raise ValueError('buffers must be a positive integer')
        if not isinstance(source, (int, str)) or isinstance(source, bool):
            raise ValueError('source must be a camera index or device path')
        self.source = f'/dev/video{source}' if isinstance(source, int) else source
        self.resolution = tuple(resolution)
        self.fps, self.buffers = float(fps), buffers
        self.report_fps, self.reconnect_delay = report_fps, reconnect_delay
        self.source_pipeline = source_pipeline
        self.new_jpeg_signal = Signal('new original camera JPEG')
        self.new_frame_signal = Signal('new decoded camera BGR frame')
        self.jpeg = self.frame = None
        self.measured_fps = 0.0
        self._thread = None
        self._stopping = True

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            if self._stopping:
                raise RuntimeError('camera is still stopping')
            return self
        self._stopping = False
        self._thread = Thread(target=self._run, name='camera', daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout: float = 5.0):
        self._stopping = True
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError('camera capture has not stopped yet')

    def _create_pipeline(self):
        init_gst()
        rate = Fraction(self.fps).limit_denominator(1001)
        width, height = self.resolution
        source = self.source_pipeline or 'v4l2src name=camera_source io-mode=mmap'
        pipeline = Gst.parse_launch(
            f'{source} ! image/jpeg,width={width},height={height},framerate={rate.numerator}/{rate.denominator} '
            f'! tee name=split split. ! queue leaky=downstream max-size-buffers={self.buffers} '
            f'max-size-bytes=0 max-size-time=0 ! appsink name=jpeg_sink sync=false async=false '
            f'max-buffers={self.buffers} drop=true '
            'split. ! queue leaky=downstream max-size-buffers=1 max-size-bytes=0 max-size-time=0 '
            '! valve name=decode_gate drop=true drop-mode=transform-to-gap '
            '! jpegdec ! videoconvert ! video/x-raw,format=BGR '
            '! appsink name=bgr_sink sync=false async=false max-buffers=1 drop=true')
        if self.source_pipeline is None:
            pipeline.get_by_name('camera_source').set_property('device', self.source)
        return pipeline

    def _decoded_frame(self, sample):
        info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
        buffer = sample.get_buffer()
        ok, mapped = buffer.map(Gst.MapFlags.READ)
        if not ok:
            raise OSError('Could not map a decoded camera frame')
        try:
            return np.ndarray((info.height, info.width, 3), dtype=np.uint8, buffer=mapped.data,
                              offset=info.offset[0], strides=(info.stride[0], 3, 1)).copy()
        finally:
            buffer.unmap(mapped)

    def _capture(self, pipeline):
        raw = pipeline.get_by_name('jpeg_sink')
        decoded = pipeline.get_by_name('bgr_sink')
        gate = pipeline.get_by_name('decode_gate')
        bus = pipeline.get_bus()
        if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            check_bus(bus)
            raise OSError('Could not start the camera pipeline')
        logger.debug('Camera endpoint=%r backend=GStreamer source=%s; JPEG + optional BGR; target=%dx%d',
                     realpath(self.source), self.source_pipeline or 'v4l2src', *self.resolution)
        frames = 0
        measured_at = last_frame = monotonic()
        logged_caps = False
        while not self._stopping:
            gate.set_property('drop', not bool(self.new_frame_signal.receivers))
            check_bus(bus)
            sample = raw.emit('try-pull-sample', 100 * Gst.MSECOND)
            if self._stopping:
                break
            now = monotonic()
            if sample is not None:
                caps = sample.get_caps()
                shape = caps.get_structure(0)
                buffer = sample.get_buffer()
                self.jpeg = JpegFrame(buffer.extract_dup(0, buffer.get_size()),
                                      shape.get_value('width'), shape.get_value('height'))
                if not logged_caps:
                    logger.debug('Camera negotiated caps: %s', caps.to_string())
                    logged_caps = True
                self.new_jpeg_signal.trigger(self.jpeg)
                frames += 1
                last_frame = now
            elif now - last_frame > 2:
                raise OSError('Camera stopped delivering JPEG frames')
            if self.new_frame_signal.receivers:
                sample = decoded.emit('try-pull-sample', 0)
                if sample is not None:
                    self.frame = self._decoded_frame(sample)
                    self.new_frame_signal.trigger(self.frame)
            else:
                self.frame = None
            if now - measured_at >= 5:
                self.measured_fps = frames / (now - measured_at)
                if self.report_fps:
                    logger.debug('Camera %r: delivered %.2f JPEG FPS', self.source, self.measured_fps)
                frames, measured_at = 0, now

    def _run(self):
        while not self._stopping:
            pipeline = None
            try:
                pipeline = self._create_pipeline()
                self._capture(pipeline)
            except (GLib.Error, OSError) as exc:
                if not self._stopping:
                    logger.warning('Camera %r: %s; reconnecting', self.source, exc)
            finally:
                if pipeline is not None:
                    pipeline.set_state(Gst.State.NULL)
                self.jpeg = self.frame = None
                self.measured_fps = 0.0
            retry_at = monotonic() + self.reconnect_delay
            while not self._stopping:
                remaining = retry_at - monotonic()
                if remaining <= 0:
                    break
                sleep(min(remaining, 0.05))
