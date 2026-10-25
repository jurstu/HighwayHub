"""Recording metadata, bounded thumbnail caching, and file operations."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2

from .recorder import CameraRecorder

VIDEO_SUFFIXES = {'.avi', '.mp4', '.mkv', '.mov', '.webm'}
SORT_OPTIONS = {
    'date_desc': 'Newest first', 'date_asc': 'Oldest first',
    'size_desc': 'Largest first', 'size_asc': 'Smallest first',
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


class VideoLibrary:
    def __init__(self, recorder: CameraRecorder):
        self.recorder = recorder
        self._thumbnails = {}

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

    def list_videos(self, order: str = 'date_desc') -> tuple[Video, ...]:
        if order not in SORT_OPTIONS:
            raise ValueError('Invalid sort order')
        videos = []
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
            videos.append(Video(path.name, info.st_size, info.st_mtime_ns, self._active(path),
                                _recorded_ns(path, info.st_mtime_ns)))
        field = 'recorded_ns' if order.startswith('date_') else 'size'
        return tuple(sorted(videos, key=lambda video: (getattr(video, field), video.name),
                            reverse=order.endswith('_desc')))

    def completed_file(self, name: str) -> Path:
        path = self._path(name)
        if self._active(path):
            raise PermissionError('This clip is still recording. Stop recording first.')
        return path

    def delete(self, name: str):
        path = self.completed_file(name)
        path.unlink()
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
