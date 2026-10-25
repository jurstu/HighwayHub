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
from camera_stuff.video_library import VideoLibrary
from webgui.recordings_screen import RecordingsScreen


class VideoLibraryTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix='highwayhub-library-', dir='/tmp')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'recordings'
        self.recorder = CameraRecorder(self.root)
        self.library = VideoLibrary(self.recorder)
        self.screen = RecordingsScreen(self.library)

    def video(self, name='drive.avi'):
        self.root.mkdir(exist_ok=True)
        path = self.root / name
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 30, (160, 120))
        self.assertTrue(writer.isOpened())
        try:
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

    def test_active_file_cannot_be_downloaded_deleted_or_decoded(self):
        path = self.video()
        self.recorder.active_path = path
        self.assertIsNone(self.recorder.status.path)  # Status may not have been published yet.
        self.assertTrue(self.library.list_videos()[0].active)
        with self.assertRaises(PermissionError):
            self.library.completed_file(path.name)
        with self.assertRaises(PermissionError):
            self.library.delete(path.name)
        with patch('camera_stuff.video_library.cv2.VideoCapture') as capture:
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
