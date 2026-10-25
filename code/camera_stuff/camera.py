"""Threaded OpenCV capture; GStreamer pipelines work with CAP_GSTREAMER."""

from math import isfinite
from os.path import realpath
from threading import Thread, current_thread
from time import monotonic, sleep

import cv2

from logging_setup import get_logger
from Util import Signal

logger = get_logger(__name__)


class Camera:
    """Keep the latest BGR frame and emit it through ``new_frame_signal``.

    Connect receivers before calling start(). Receivers run on the camera
    thread: keep them quick and treat frames as read-only (copy before editing).
    Call start/stop from one controlling thread; a receiver may also call stop.
    Only the capture thread touches VideoCapture. No locks or frame queues.

    fps requests a hardware rate; fourcc="MJPG" avoids slow uncompressed USB
    modes on cameras that support it. Negotiated and measured rates are logged.
    buffers controls driver buffers; one can starve capture during MJPEG decode.

    A GStreamer source must end in ``appsink drop=true max-buffers=1 sync=false``
    and requires an OpenCV build with GStreamer support.
    """

    def __init__(
        self,
        source: int | str = 0,
        resolution: tuple[int, int] = (1280, 720),
        *,
        fps: float = 30.0,
        fourcc: str | None = None,
        buffers: int = 10,
        backend: int = cv2.CAP_ANY,
        reconnect_delay: float = 1.0,
    ):
        if len(resolution) != 2 or any(type(n) is not int or n <= 0 for n in resolution):
            raise ValueError("resolution must be (width, height) in positive integers")
        if not isfinite(reconnect_delay) or reconnect_delay <= 0:
            raise ValueError("reconnect_delay must be finite and positive")
        if not isfinite(fps) or fps <= 0:
            raise ValueError("fps must be finite and positive")
        if fourcc is not None and (len(fourcc) != 4 or not fourcc.isascii()):
            raise ValueError("fourcc must be four ASCII characters, e.g. 'MJPG'")
        if type(buffers) is not int or buffers < 1:
            raise ValueError('buffers must be a positive integer')
        self.source = source
        self.resolution = tuple(resolution)
        self.fps = float(fps)
        self.fourcc = fourcc
        self.buffers = buffers
        self.measured_fps = 0.0
        self.backend = backend
        self.reconnect_delay = reconnect_delay
        self.new_frame_signal = Signal("new camera frame")
        self.frame = None
        self._thread = None
        self._stopping = True

    def start(self):
        """Start capture, or return self if already running."""
        if self._thread is not None and self._thread.is_alive():
            if self._stopping:
                raise RuntimeError("camera is still stopping")
            return self
        self._stopping = False
        self._thread = Thread(target=self._run, name="camera", daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout: float = 5.0):
        """Request shutdown and wait up to timeout seconds for resource release.

        Native camera reads cannot always be interrupted. Raise TimeoutError if
        one remains blocked; the worker will release capture when it returns.
        From a signal receiver, request shutdown without joining this thread.
        """
        self._stopping = True
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError("camera capture has not stopped yet")

    def _log_capture(self, capture):
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        code = int(capture.get(cv2.CAP_PROP_FOURCC))
        fourcc = ''.join(chr((code >> (8 * i)) & 255) for i in range(4)) if code > 0 else 'unknown'
        endpoint = realpath(self.source) if isinstance(self.source, str) and self.source.startswith('/dev/') else self.source
        logger.debug(
            "Camera source=%r endpoint=%r backend=%s; requested=%dx%d @ %.2f FPS format=%s; "
            "negotiated=%dx%d @ %.2f FPS format=%s buffers=%g",
            self.source, endpoint, capture.getBackendName(), *self.resolution, self.fps,
            self.fourcc or 'auto', width, height, fps, fourcc, capture.get(cv2.CAP_PROP_BUFFERSIZE),
        )
        if fps > 0 and fps < self.fps * 0.95:
            logger.warning("Camera negotiated %.2f FPS below requested %.2f FPS; check format/resolution",
                           fps, self.fps)
        if self.fourcc and code > 0 and fourcc != self.fourcc:
            logger.warning("Camera negotiated format %r instead of %r", fourcc, self.fourcc)

    def _run(self):
        while not self._stopping:
            capture = None
            try:
                capture = cv2.VideoCapture()
                if not capture.open(self.source, self.backend):
                    raise OSError("could not open camera")
                width, height = self.resolution
                # Set the transport format first: 1080p YUYV may be limited to 5 FPS.
                if self.fourcc is not None:
                    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                capture.set(cv2.CAP_PROP_FPS, self.fps)
                # Allow capture while OpenCV decodes another buffer (one can starve V4L2).
                capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffers)  # Backend-dependent.
                self._log_capture(capture)
                frames = 0
                measured_at = monotonic()
                read_seconds = processing_seconds = 0.0
                while not self._stopping:
                    read_at = monotonic()
                    ok, frame = capture.read()
                    read_done = monotonic()
                    if self._stopping:
                        break
                    if not ok or frame is None or frame.size == 0:
                        raise OSError("camera stopped delivering frames")
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv2.resize(frame, (width, height))
                    self.frame = frame
                    self.new_frame_signal.trigger(frame)
                    frames += 1
                    now = monotonic()
                    read_seconds += read_done - read_at
                    processing_seconds += now - read_done
                    if now - measured_at >= 5:
                        self.measured_fps = frames / (now - measured_at)
                        logger.debug("Camera %r: delivered %.2f FPS; read/decode=%.2f ms/frame; "
                                     "resize/signals=%.2f ms/frame",
                                     self.source, self.measured_fps, read_seconds * 1000 / frames,
                                     processing_seconds * 1000 / frames)
                        frames, measured_at = 0, now
                        read_seconds = processing_seconds = 0.0
            except (cv2.error, OSError) as exc:
                if not self._stopping:
                    logger.warning("Camera %r: %s; reconnecting", self.source, exc)
            finally:
                self.frame = None
                self.measured_fps = 0.0
                if capture is not None:
                    capture.release()

            # Poll a plain flag so shutdown stays responsive without locks/events.
            retry_at = monotonic() + self.reconnect_delay
            while not self._stopping:
                remaining = retry_at - monotonic()
                if remaining <= 0:
                    break
                sleep(min(remaining, 0.05))
