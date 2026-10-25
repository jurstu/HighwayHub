"""Recording metadata, bounded thumbnail caching, and file operations."""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

import cv2

from .recorder import CameraRecorder

VIDEO_SUFFIXES = {'.avi', '.mp4', '.mkv', '.mov', '.webm'}
SORT_OPTIONS = {
    'date_desc': 'Newest first', 'date_asc': 'Oldest first',
    'size_desc': 'Largest first', 'size_asc': 'Smallest first',
    'duration_desc': 'Longest first', 'duration_asc': 'Shortest first',
}


def _recorded_ns(path: Path, fallback: int) -> int:
    """Decode the recorder's UTC filename; keep mtime for custom/invalid names."""
    if path.stem.startswith('camera-'):
        for pattern in ('camera-%Y%m%dT%H%M%S.%fZ', 'camera-%Y%m%dT%H%M%SZ'):
            try:
                date = datetime.strptime(path.stem, pattern)
            except ValueError:
                continue
            seconds = int(date.replace(tzinfo=timezone.utc, microsecond=0).timestamp())
            return seconds * 1_000_000_000 + date.microsecond * 1000
    return fallback


@dataclass(frozen=True)
class Video:
    name: str
    size: int
    modified_ns: int
    active: bool
    recorded_ns: int
    duration: float | None = None


class VideoLibrary:
    def __init__(self, recorder: CameraRecorder):
        self.recorder = recorder
        self._thumbnails = {}
        self._durations = {}

    @property
    def directory(self) -> Path:
        return self.recorder.recordings_dir.expanduser().resolve()

    def _active(self, path: Path) -> bool:
        active = self.recorder.active_path
        return active is not None and path == active.expanduser().resolve()

    def _path(self, name: str) -> Path:
        if not name or name != Path(name).name or '\\' in name:
            raise FileNotFoundError('Recording not found')
        path = self.directory / name
        if path.suffix.lower() not in VIDEO_SUFFIXES or path.is_symlink() or not path.is_file():
            raise FileNotFoundError('Recording not found')
        return path

    def _duration(self, path: Path, info) -> float | None:
        key = str(path)
        signature = (info.st_mtime_ns, info.st_size)
        cached = self._durations.get(key)
        if cached is not None and cached[:2] == signature:
            return cached[2]
        duration = None
        capture = cv2.VideoCapture()
        try:
            # Read container metadata in raw-packet mode; do not decode frames
            # or initialize an image decoder just to determine clip length.
            if capture.open(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_FORMAT, -1]):
                fps = capture.get(cv2.CAP_PROP_FPS)
                frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
                if isfinite(fps) and fps > 0 and isfinite(frames) and frames > 0:
                    duration = frames / fps
        except cv2.error:
            pass
        finally:
            capture.release()
        self._durations[key] = (*signature, duration)
        return duration

    def list_videos(self, order: str = 'date_desc') -> tuple[Video, ...]:
        if order not in SORT_OPTIONS:
            raise ValueError('Invalid sort order')
        videos = []
        existing = set()
        try:
            paths = list(self.directory.iterdir())
        except FileNotFoundError:
            return ()
        for path in paths:
            if path.suffix.lower() not in VIDEO_SUFFIXES or path.is_symlink():
                continue
            try:
                if not path.is_file():
                    continue
                info = path.stat()
            except FileNotFoundError:  # Another browser may have just deleted it.
                continue
            existing.add(str(path))
            active = self._active(path)
            videos.append(Video(path.name, info.st_size, info.st_mtime_ns, active,
                                _recorded_ns(path, info.st_mtime_ns),
                                None if active else self._duration(path, info)))
        for key in tuple(self._durations):
            if key not in existing:
                self._durations.pop(key, None)
        field = {'date': 'recorded_ns', 'size': 'size', 'duration': 'duration'}[order.split('_')[0]]
        known = [video for video in videos if getattr(video, field) is not None]
        unknown = [video for video in videos if getattr(video, field) is None]
        return tuple(sorted(known, key=lambda video: (getattr(video, field), video.name),
                            reverse=order.endswith('_desc'))
                     + sorted(unknown, key=lambda video: video.name))

    def completed_file(self, name: str) -> Path:
        path = self._path(name)
        if self._active(path):
            raise PermissionError('This clip is still recording. Stop recording first.')
        return path

    def delete(self, name: str):
        path = self.completed_file(name)
        path.unlink()
        self._durations.pop(str(path), None)
        for key in tuple(self._thumbnails):
            if key[0] == str(path):
                self._thumbnails.pop(key, None)

    def thumbnail(self, name: str) -> bytes | None:
        path = self._path(name)
        if self._active(path):
            return None
        info = path.stat()
        key = (str(path), info.st_mtime_ns, info.st_size)
        cached = self._thumbnails.get(key)
        if cached is not None:
            return cached
        capture = cv2.VideoCapture()
        try:
            if not capture.open(str(path)):
                return None
            ok, frame = capture.read()
            if not ok or frame is None or frame.size == 0:
                return None
            height, width = frame.shape[:2]
            thumbnail = cv2.resize(frame, (320, max(1, round(height * 320 / width))),
                                   interpolation=cv2.INTER_AREA)
            ok, jpeg = cv2.imencode('.jpg', thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                return None
            data = jpeg.tobytes()
            if len(self._thumbnails) >= 128:
                self._thumbnails.pop(next(iter(self._thumbnails), None), None)
            self._thumbnails[key] = data
            return data
        except cv2.error:
            return None
        finally:
            capture.release()
