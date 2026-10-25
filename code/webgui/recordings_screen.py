"""Browse, download and delete recorded videos."""

from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from nicegui import ui
from starlette.responses import FileResponse, Response

from camera_stuff.video_library import SORT_OPTIONS, VideoLibrary
from .main_screen import CSS
from .page_timer import PageTimer

RECORDINGS_PATH = '/camera/recordings'
DOWNLOAD_PATH = '/camera/recordings/{name}/download'
THUMBNAIL_PATH = '/camera/recordings/{name}/thumbnail.jpg'
PLACEHOLDER = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
<rect width="320" height="180" fill="#142126"/><rect x="116" y="62" width="66" height="52" rx="9"
fill="none" stroke="#71868a" stroke-width="3"/><path d="M182 78l25-14v48l-25-14z" fill="#71868a"/></svg>'''
RECORDINGS_CSS = '''
.recordings-toolbar { display: flex; justify-content: space-between; align-items: center;
  gap: 16px; flex-wrap: wrap; }
.recordings-title { font-size: 30px; font-weight: 800; letter-spacing: -.04em; }
.recordings-subtitle { color: #829198; font-size: 13px; }
.recordings-actions { display: flex; gap: 10px; align-items: center; }
.recordings-sort { width: 190px; }
.recordings-scroll { flex: 1; min-height: 0; overflow: auto; padding: 2px 2px 16px; }
.recordings-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(265px, 1fr)); }
.recording-card { padding: 0 !important; background: #10191e !important; border: 1px solid #293c42;
  border-radius: 16px !important; overflow: hidden; box-shadow: none !important; }
.recording-thumbnail { position: relative; width: 100%; aspect-ratio: 16/9; background: #142126; }
.recording-thumbnail .q-img { width: 100%; height: 100%; }
.recording-active { position: absolute; top: 12px; left: 12px; background: #331b1b;
  color: #ff9595; border: 1px solid #703030; border-radius: 99px; padding: 5px 10px;
  font-size: 10px; font-weight: 800; letter-spacing: .1em; }
.recording-body { padding: 16px; width: 100%; box-sizing: border-box; }
.recording-name { color: #f2f6ee; font-size: 13px; font-weight: 750; overflow-wrap: anywhere; }
.recording-meta { display: flex; justify-content: space-between; gap: 8px; color: #829198;
  font-size: 11px; margin: 9px 0 16px; }
.recording-buttons { display: flex; justify-content: space-between; gap: 8px; }
.recordings-empty { min-height: 240px; display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 12px; color: #829198; }
.recordings-more { display: flex; justify-content: center; padding: 20px; }
.recordings-back { border: 1px solid #40554b; border-radius: 10px !important; }
@media (max-width: 600px) {
  .recordings-title { font-size: 25px; }
  .recordings-grid { grid-template-columns: 1fr; }
  .recordings-actions { width: 100%; }
  .recordings-sort { flex: 1; }
}
'''


def _size(value: int) -> str:
    number = float(value)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if number < 1024 or unit == 'TB':
            return f'{number:.1f} {unit}' if unit != 'B' else f'{int(number)} B'
        number /= 1024


class RecordingsScreen:
    def __init__(self, library: VideoLibrary):
        self.library = library

    def download_response(self, name: str) -> FileResponse:
        try:
            path = self.library.completed_file(name)
            return FileResponse(path, filename=path.name, media_type='application/octet-stream',
                                headers={'Cache-Control': 'no-store'})
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(409, str(exc)) from exc

    def thumbnail_response(self, name: str) -> Response:
        try:
            data = self.library.thumbnail(name)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        return Response(data if data is not None else PLACEHOLDER,
                        media_type='image/jpeg' if data is not None else 'image/svg+xml',
                        headers={'Cache-Control': 'no-cache'})

    def spawn_gui(self):
        ui.dark_mode().enable()
        ui.add_css(CSS + RECORDINGS_CSS)
        state = {'order': 'date_desc', 'limit': 24}
        previous = None
        selected = None

        def delete_selected():
            try:
                self.library.delete(selected)
                ui.notify('Recording deleted', type='positive')
            except (OSError, ValueError) as exc:
                ui.notify(str(exc), type='negative')
            dialog.close()
            refresh(force=True)

        with ui.dialog() as dialog, ui.card().classes('bg-[#142126] text-white'):
            ui.label('Delete recording?').classes('text-xl font-bold')
            delete_name = ui.label().classes('break-all')
            ui.label('This permanently removes the video from this device.').classes('text-sm text-gray-400')
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat no-caps')
                ui.button('Delete recording', icon='delete', on_click=delete_selected).props('color=negative no-caps')

        def ask_delete(name):
            nonlocal selected
            selected = name
            delete_name.set_text(name)
            dialog.open()

        @ui.refreshable
        def cards(videos, error=''):
            if not videos:
                with ui.element('div').classes('recordings-empty'):
                    ui.icon('video_library', size='48px')
                    ui.label('Could not read recordings' if error else 'No recordings yet').classes('text-xl font-bold')
                    ui.label(error or 'Your saved camera clips will appear here.')
                return
            with ui.element('div').classes('recordings-grid'):
                for video in videos[:state['limit']]:
                    with ui.card().classes('recording-card'):
                        with ui.element('div').classes('recording-thumbnail'):
                            url = THUMBNAIL_PATH.format(name=quote(video.name, safe=''))
                            ui.image(f'{url}?v={video.modified_ns}-{video.size}').props(
                                'ratio=1.777778 fit=cover loading=lazy no-spinner no-transition')
                            if video.active:
                                ui.label('RECORDING').classes('recording-active')
                        with ui.element('div').classes('recording-body'):
                            ui.label(video.name).classes('recording-name')
                            with ui.element('div').classes('recording-meta'):
                                date = datetime.fromtimestamp(video.recorded_ns / 1e9, ZoneInfo('Europe/Warsaw'))
                                ui.label(date.strftime('%d %b %Y · %H:%M'))
                                ui.label(_size(video.size))
                            with ui.element('div').classes('recording-buttons'):
                                download = ui.button('Download', icon='download', on_click=lambda name=video.name:
                                    ui.download.from_url(DOWNLOAD_PATH.format(name=quote(name, safe=''))))
                                download.props('flat dense no-caps color=light-green-4')
                                delete = ui.button('Delete', icon='delete_outline',
                                                   on_click=lambda name=video.name: ask_delete(name))
                                delete.props('flat dense no-caps color=red-4')
                                download.set_enabled(not video.active)
                                delete.set_enabled(not video.active)
            if len(videos) > state['limit']:
                with ui.element('div').classes('recordings-more'):
                    ui.button('Show more', on_click=show_more).props('flat no-caps color=light-green-4')

        def refresh(*, force=False):
            nonlocal previous
            try:
                videos = self.library.list_videos(state['order'])
                error = ''
            except OSError as exc:
                videos, error = (), str(exc)
            snapshot = (videos, error, state['limit'])
            if force or snapshot != previous:
                summary.set_text(f'{len(videos)} videos · {_size(sum(video.size for video in videos))}')
                cards.refresh(videos, error)
                previous = snapshot

        def change_sort(event):
            state.update(order=event.value, limit=24)
            refresh(force=True)

        def show_more():
            state['limit'] += 24
            refresh(force=True)

        with ui.element('main').classes('dashboard'):
            with ui.element('header').classes('topbar'):
                with ui.element('div').classes('brand'):
                    ui.label('H').classes('brand-mark')
                    with ui.element('div'):
                        ui.html('HIGHWAY<span>HUB</span>', sanitize=False).classes('brand-name')
                        ui.label('VIDEO LIBRARY').classes('brand-sub')
                ui.button('Back to camera', icon='arrow_back', on_click=lambda: ui.navigate.to('/camera')) \
                    .props('flat no-caps color=light-green-4').classes('recordings-back')
            with ui.element('div').classes('recordings-toolbar'):
                with ui.element('div'):
                    ui.label('Your recordings').classes('recordings-title')
                    summary = ui.label().classes('recordings-subtitle')
                with ui.element('div').classes('recordings-actions'):
                    ui.select(SORT_OPTIONS, value=state['order'], label='Sort by', on_change=change_sort) \
                        .props('outlined dense options-dense color=light-green-4').classes('recordings-sort')
                    ui.button('Refresh', icon='refresh', on_click=lambda: refresh(force=True)) \
                        .props('flat no-caps color=light-green-4')
            with ui.element('section').classes('recordings-scroll'):
                cards(())
            with ui.element('footer').classes('statusbar'):
                ui.label('HIGHWAYHUB / RECORDINGS')
                ui.label('SAVED ON THIS DEVICE')
        refresh()
        PageTimer(2, refresh)
