"""Run with PYTHONPATH=code python -m unittest camera_stuff.test_video_library."""

from os import utime
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import cv2
from fastapi import HTTPException
import numpy as np

from camera_stuff.recorder import CameraRecorder
from camera_stuff.h264_writer import H264VideoWriter
from camera_stuff.jpeg_frame import JpegFrame
from camera_stuff.video_library import VideoLibrary
from webgui.recordings_screen import RecordingsScreen, _duration


class VideoLibraryTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix='highwayhub-library-', dir='/tmp')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'recordings'
        self.recorder = CameraRecorder(self.root)
        self.library = VideoLibrary(self.recorder)
        self.screen = RecordingsScreen(self.library)

    def video(self, name='drive.avi', *, frames=1, fps=30):
        self.root.mkdir(exist_ok=True)
        path = self.root / name
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), fps, (160, 120))
        self.assertTrue(writer.isOpened())
        try:
            for _ in range(frames):
                writer.write(np.full((120, 160, 3), 80, dtype=np.uint8))
        finally:
            writer.release()
        return path

    def test_missing_directory_is_an_empty_library(self):
        self.assertEqual(self.library.list_videos(), ())
        self.assertFalse(self.root.exists())

    def test_sorts_by_date_and_size_in_both_directions(self):
        self.root.mkdir()
        for index, (name, size) in enumerate([('old.avi', 10), ('middle.mp4', 20), ('new.avi', 30)]):
            path = self.root / name
            path.write_bytes(b'x' * size)
            utime(path, ns=(index + 1, index + 1))
        for order, expected in [
            ('date_desc', ['new.avi', 'middle.mp4', 'old.avi']),
            ('date_asc', ['old.avi', 'middle.mp4', 'new.avi']),
            ('size_desc', ['new.avi', 'middle.mp4', 'old.avi']),
            ('size_asc', ['old.avi', 'middle.mp4', 'new.avi']),
        ]:
            with self.subTest(order=order):
                self.assertEqual([video.name for video in self.library.list_videos(order)], expected)
        with self.assertRaises(ValueError):
            self.library.list_videos('invalid')

    def test_ignores_directories_non_video_files_and_symlinks(self):
        path = self.video()
        (self.root / 'notes.txt').write_text('notes')
        (self.root / 'directory.avi').mkdir()
        (self.root / 'alias.avi').symlink_to(path)
        self.assertEqual([video.name for video in self.library.list_videos()], [path.name])

    def test_duration_sorting_keeps_active_and_unreadable_files_last(self):
        for name, seconds in [('short.avi', 1), ('long.avi', 3), ('middle.avi', 2)]:
            self.video(name, frames=10 * seconds, fps=10)
        self.recorder.active_path = self.video('live.avi')
        (self.root / 'bad.mp4').write_bytes(b'incomplete video')
        for order, names in [
            ('duration_asc', ['short.avi', 'middle.avi', 'long.avi', 'bad.mp4', 'live.avi']),
            ('duration_desc', ['long.avi', 'middle.avi', 'short.avi', 'bad.mp4', 'live.avi']),
        ]:
            with self.subTest(order=order):
                videos = self.library.list_videos(order)
                self.assertEqual([video.name for video in videos], names)
                durations = {video.name: video.duration for video in videos}
                self.assertEqual(durations, {'short.avi': 1, 'middle.avi': 2, 'long.avi': 3,
                                             'bad.mp4': None, 'live.avi': None})

    def test_duration_is_cached_until_file_changes_and_removed_on_delete(self):
        path = self.video(frames=20, fps=10)
        with patch('camera_stuff.video_library.cv2.VideoCapture', wraps=cv2.VideoCapture) as capture:
            self.assertEqual(self.library.list_videos()[0].duration, 2)
            self.assertEqual(self.library.list_videos()[0].duration, 2)
            capture.assert_called_once()
            info = path.stat()
            utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
            self.assertEqual(self.library.list_videos()[0].duration, 2)
            self.assertEqual(capture.call_count, 2)
        self.library.delete(path.name)
        self.assertNotIn(str(path), self.library._durations)

    def test_unknown_duration_is_cached_without_decoding_frames(self):
        self.video()
        for fps, frames in [(0, 10), (float('nan'), 10), (float('inf'), 10),
                            (30, 0), (30, float('nan')), (30, float('inf'))]:
            with self.subTest(fps=fps, frames=frames):
                self.library._durations.clear()
                capture = Mock()
                capture.open.return_value = True
                capture.get.side_effect = [fps, frames]
                with patch('camera_stuff.video_library.cv2.VideoCapture', return_value=capture) as factory:
                    self.assertIsNone(self.library.list_videos()[0].duration)
                    self.assertIsNone(self.library.list_videos()[0].duration)
                factory.assert_called_once()
                capture.read.assert_not_called()
                capture.release.assert_called_once()

    def test_duration_format_handles_minutes_hours_and_unknown(self):
        for seconds, expected in [(None, '—'), (0, '00:00'), (15.2, '00:15'),
                                  (65, '01:05'), (3599.6, '1:00:00'), (3661, '1:01:01')]:
            with self.subTest(seconds=seconds):
                self.assertEqual(_duration(seconds), expected)

    def test_filename_dates_override_modification_time_for_date_sorting(self):
        self.root.mkdir()
        names = ['camera-20261025T120000.123456Z.avi', 'camera-20261025T120000.123457Z.avi']
        for index, name in enumerate(names):
            path = self.root / name
            path.write_bytes(b'video')
            utime(path, ns=(20 - index, 20 - index))  # Opposite order to filename timestamps.
        newest = self.library.list_videos('date_desc')
        self.assertEqual([video.name for video in newest], names[::-1])
        self.assertEqual([video.name for video in self.library.list_videos('date_asc')], names)
        seconds = int(datetime(2026, 10, 25, 12, tzinfo=timezone.utc).timestamp())
        self.assertEqual(newest[0].recorded_ns, seconds * 1_000_000_000 + 123457000)
        self.assertEqual(newest[0].modified_ns, 19)

    def test_filename_date_without_fraction_and_invalid_name_fallback(self):
        self.root.mkdir()
        for name in ['camera-20261025T120000Z.avi', 'camera-20261325T120000.000000Z.avi', 'custom.avi']:
            path = self.root / name
            path.write_bytes(b'video')
            utime(path, ns=(123456789, 123456789))
        videos = {video.name: video for video in self.library.list_videos()}
        seconds = int(datetime(2026, 10, 25, 12, tzinfo=timezone.utc).timestamp())
        self.assertEqual(videos['camera-20261025T120000Z.avi'].recorded_ns, seconds * 1_000_000_000)
        self.assertEqual(videos['camera-20261325T120000.000000Z.avi'].recorded_ns, 123456789)
        self.assertEqual(videos['custom.avi'].recorded_ns, 123456789)

    def test_thumbnail_is_jpeg_and_reused_until_file_changes(self):
        path = self.video()
        data = self.library.thumbnail(path.name)
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(image.shape, (240, 320, 3))
        with patch('camera_stuff.video_library.cv2.VideoCapture') as capture:
            self.assertEqual(self.library.thumbnail(path.name), data)
        capture.assert_not_called()
        info = path.stat()
        utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        with patch('camera_stuff.video_library.cv2.VideoCapture', wraps=cv2.VideoCapture) as capture:
            self.assertIsNotNone(self.library.thumbnail(path.name))
        capture.assert_called_once()

    def test_h264_mp4_supports_thumbnail_download_and_delete(self):
        self.root.mkdir()
        path = self.recorder.suggest_path()
        ok, jpeg = cv2.imencode('.jpg', np.full((120, 160, 3), 80, dtype=np.uint8))
        self.assertTrue(ok)
        writer = H264VideoWriter(path, 30, (160, 120), bitrate_kbps=6000)
        try:
            writer.write(JpegFrame(jpeg.tobytes(), 160, 120))
        finally:
            writer.close()
        video = self.library.list_videos()[0]
        self.assertEqual(video.name, path.name)
        self.assertAlmostEqual(video.duration, 1 / 30)
        response = self.screen.thumbnail_response(path.name)
        self.assertEqual(response.media_type, 'image/jpeg')
        thumbnail = cv2.imdecode(np.frombuffer(response.body, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(thumbnail.shape, (240, 320, 3))
        self.assertEqual(Path(self.screen.download_response(path.name).path), path)
        self.library.delete(path.name)
        self.assertFalse(path.exists())

    def test_active_file_cannot_be_downloaded_deleted_or_decoded(self):
        path = self.video()
        self.recorder.active_path = path
        self.assertIsNone(self.recorder.status.path)  # Status may not have been published yet.
        with self.assertRaises(PermissionError):
            self.library.completed_file(path.name)
        with self.assertRaises(PermissionError):
            self.library.delete(path.name)
        with patch('camera_stuff.video_library.cv2.VideoCapture') as capture:
            video = self.library.list_videos()[0]
            self.assertTrue(video.active)
            self.assertIsNone(video.duration)
            self.assertIsNone(self.library.thumbnail(path.name))
        capture.assert_not_called()
        self.assertTrue(path.exists())

    def test_delete_removes_only_the_selected_clip(self):
        selected = self.video('selected.avi')
        retained = self.video('retained.avi')
        self.library.thumbnail(selected.name)
        self.library.delete(selected.name)
        self.assertFalse(selected.exists())
        self.assertTrue(retained.exists())
        with self.assertRaises(FileNotFoundError):
            self.library.thumbnail(selected.name)

    def test_rejects_paths_outside_recordings_folder(self):
        self.root.mkdir()
        outside = Path(self.directory.name) / 'outside.avi'
        outside.write_bytes(b'keep this')
        (self.root / 'alias.avi').symlink_to(outside)
        for name in ['../outside.avi', str(outside), 'folder\\outside.avi', 'alias.avi', 'notes.txt']:
            with self.subTest(name=name):
                for action in [self.library.completed_file, self.library.delete, self.library.thumbnail]:
                    with self.assertRaises(FileNotFoundError):
                        action(name)
        self.assertEqual(outside.read_bytes(), b'keep this')

    def test_download_response_streams_file_with_original_filename(self):
        path = self.video('road trip.avi')
        response = self.screen.download_response(path.name)
        self.assertEqual(Path(response.path), path)
        self.assertIn('attachment;', response.headers['content-disposition'])
        self.assertIn('road%20trip.avi', response.headers['content-disposition'])

    def test_thumbnail_response_has_placeholder_for_unreadable_video(self):
        path = self.video()
        capture = Mock()
        capture.open.return_value = False
        with patch('camera_stuff.video_library.cv2.VideoCapture', return_value=capture):
            response = self.screen.thumbnail_response(path.name)
        self.assertEqual(response.media_type, 'image/svg+xml')
        capture.release.assert_called_once()

    def test_http_routes_reject_missing_and_active_files(self):
        with self.assertRaises(HTTPException) as missing:
            self.screen.download_response('missing.avi')
        self.assertEqual(missing.exception.status_code, 404)
        with self.assertRaises(HTTPException) as missing_thumbnail:
            self.screen.thumbnail_response('missing.avi')
        self.assertEqual(missing_thumbnail.exception.status_code, 404)
        path = self.video()
        self.recorder.active_path = path
        with self.assertRaises(HTTPException) as active:
            self.screen.download_response(path.name)
        self.assertEqual(active.exception.status_code, 409)


if __name__ == '__main__':
    unittest.main()
