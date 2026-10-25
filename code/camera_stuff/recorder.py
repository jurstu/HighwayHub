"""Independent video recording: always receive frames, write only when enabled."""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from os import statvfs
from pathlib import Path
from subprocess import run, SubprocessError
from threading import Thread
from time import monotonic, sleep

import cv2

from logging_setup import get_logger
from Util import Signal

logger = get_logger(__name__)
RECORDINGS_DIR = Path("~/recordings").expanduser() #Path(__file__).resolve().parents[2] / 'recordings'
MIN_FREE_BYTES = 1_000_000_000


@dataclass(frozen=True)
class RecordingStatus:
    requested: bool = False
    path: Path | None = None
    last_path: Path | None = None
    started_at: float = 0.0
    error: str = ''


class CameraRecorder:
    """Own filename selection and VideoWriter on a dedicated thread.

    new_frame_signal accepts every BGR frame, even while recording is off.
    set_recording controls writing; an optional .avi path selects the next clip.
    suggest_path returns a default filename without creating anything. Existing
    files are never overwritten. Reconnects and size changes create new clips.

    A latest-frame slot bounds memory and keeps capture callbacks fast. The
    worker samples at fps, repeating fresh frames when input is slower. Frames
    older than two seconds close the clip. No locks or async functions.
    Check root disk space every five seconds; low space disables recording.
    """

    def __init__(self, recordings_dir: Path = RECORDINGS_DIR, *, fps: float = 30.0):
        if not isfinite(fps) or fps <= 0:
            raise ValueError('fps must be finite and positive')
        self.recordings_dir = Path(recordings_dir)
        self.fps = float(fps)
        self.new_frame_signal = Signal('new recorder frame')
        self.new_frame_signal.addReceiver(self.update_frame)
        self.status_signal = Signal('camera recording status')
        self.status = RecordingStatus()
        self.active_path = None
        self._latest = None
        self._request = (False, None)
        self._applied_request = self._request
        self._selected_path = None
        self._writer = None
        self._writer_size = None
        self._path = self._last_path = None
        self._started_at = 0.0
        self._error = ''
        self._space_error = ''
        self._next_space_check = 0.0
        self._thread = None
        self._stopping = True

    def update_frame(self, frame):
        self._latest = (monotonic(), frame)

    def suggest_path(self) -> Path:
        name = datetime.now(timezone.utc).strftime('camera-%Y%m%dT%H%M%S.%fZ.avi')
        return self.recordings_dir / name

    def set_recording(self, enabled: bool, path: str | Path | None = None):
        selected = Path(path) if path is not None else None
        if selected is not None and selected.suffix.lower() != '.avi':
            raise ValueError('recording path must end in .avi')
        if bool(enabled) != self._request[0] or selected is not None:
            self._request = (bool(enabled), selected)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            if self._stopping:
                raise RuntimeError('recorder is still stopping')
            return
        self._stopping = False
        self._next_space_check = 0.0
        self._thread = Thread(target=self._run, name='camera-recorder', daemon=True)
        self._thread.start()

    def stop(self):
        self._request = (False, None)
        self._stopping = True
        if self._thread is not None:
            self._thread.join(5)
            if self._thread.is_alive():
                raise TimeoutError('recorder has not stopped yet')

    def _publish(self):
        status = RecordingStatus(self._request[0], self._path, self._last_path,
                                 self._started_at, self._error)
        if status != self.status:
            self.status = status
            self.status_signal.trigger(status)

    def _finish(self):
        writer, self._writer = self._writer, None
        if writer is not None:
            try:
                writer.release()
            except cv2.error as exc:
                self._request = self._applied_request = (False, None)
                self._error = f'Could not finalize recording: {exc}'
                logger.warning('%s', self._error)
            finally:
                if self._path is not None:
                    logger.debug('Camera recording closed: %s', self._path)
                    self._last_path = self._path
                self._path = None
        self.active_path = None

    def _record(self, frame, now):
        size = (frame.shape[1], frame.shape[0])
        if self._writer is not None and self._writer_size != size:
            self._finish()
            if not self._request[0]:
                return
        if self._writer is None:
            path = self._selected_path or self.suggest_path()
            self._selected_path = None
            self.active_path = path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb'):  # Reserve exclusively; never truncate an existing clip.
                pass
            try:
                self._writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), self.fps, size)
                if not self._writer.isOpened():
                    raise OSError('Could not open the recording file')
            except (cv2.error, OSError):
                self._finish()
                path.unlink(missing_ok=True)
                raise
            self._path, self._writer_size, self._started_at = path, size, now
            logger.debug('Camera recording: %s format=MJPG size=%dx%d FPS=%.2f', path, *size, self.fps)
        self._writer.write(frame)

    def _check_space(self, now):
        if now < self._next_space_check:
            return
        self._next_space_check = now + 5
        previous = self._space_error
        try:
            run(['df', '-h', '/'], capture_output=True, text=True, check=True, timeout=1)
            # df -h rounds its output; use exact bytes for the 1 GB threshold.
            fs = statvfs('/')
            available = fs.f_bavail * fs.f_frsize
            self._space_error = ('Recording stopped: less than 1 GB available on root filesystem (/)'
                                 if available < MIN_FREE_BYTES else '')
        except (OSError, SubprocessError) as exc:
            self._space_error = f'Recording stopped: could not check root disk space: {exc}'
        if previous and not self._space_error and self._error == previous:
            self._error = ''

    def _tick(self, now):
        request = self._request
        if request is not self._applied_request:
            self._error = ''
            if request[1] is not None:
                self._finish()
            self._selected_path = request[1]
            self._applied_request = request
        self._check_space(now)
        if self._space_error:
            self._request = self._applied_request = (False, None)
            self._error = self._space_error
            self._finish()
            self._publish()
            return
        sample = self._latest
        if not self._request[0] or sample is None or now - sample[0] > 2:
            self._finish()
        else:
            try:
                self._record(sample[1], now)
            except (cv2.error, OSError) as exc:
                self._request = self._applied_request = (False, None)
                self._error = str(exc)
                self._finish()
                logger.warning('Camera recording failed: %s', exc)
        self._publish()

    def _run(self):
        try:
            while not self._stopping:
                started = monotonic()
                self._tick(started)
                sleep(max(0.001, 1 / self.fps - (monotonic() - started)))
        finally:
            self._request = (False, None)
            self._finish()
            self._publish()
