"""Standalone HighwayHub dashboard; WebguiRoot uses MainScreen.spawn_gui."""

from dataclasses import dataclass, replace
from math import isfinite
from threading import RLock
from time import time
from typing import Any, Iterable

from nicegui import ui


CSS = """
html, body, #app { width: 100%; height: 100%; margin: 0; overflow: hidden; }
body { background: #080d11; color: #f2f6ee; font-family: Inter, system-ui, sans-serif; }
.nicegui-content { padding: 0 !important; }
.dashboard { box-sizing: border-box; width: 100vw; height: 100dvh; display: flex; flex-direction: column;
  gap: 12px; padding: 16px 18px 12px; background: radial-gradient(ellipse at 50% -20%, #17252a, #080d11 70%); }
.topbar { flex: 0 0 46px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark { width: 32px; height: 32px; display: grid; place-items: center; border: 1px solid #c7f879;
  border-radius: 9px; color: #c7f879; font-size: 20px; font-weight: 900; transform: skew(-8deg); }
.brand-name { font-size: 18px; font-weight: 800; letter-spacing: .07em; line-height: 1; }
.brand-name span { color: #c7f879; }
.brand-sub { color: #829198; font-size: 9px; font-weight: 700; letter-spacing: .25em; margin-top: 5px; }
.topbar-center { color: #829198; font-size: 10px; font-weight: 800; letter-spacing: .18em; }
.preview-pill { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid #35473c;
  border-radius: 99px; background: #152019; color: #c7f879; font-size: 10px; font-weight: 800; letter-spacing: .12em; }
.preview-dot { width: 6px; height: 6px; border-radius: 50%; background: #c7f879; box-shadow: 0 0 9px #c7f879; }
.dashboard-grid { flex: 1; min-height: 0; display: grid; gap: 12px;
  grid-template-columns: minmax(0,1fr) minmax(0,2.12fr) minmax(0,1fr);
  grid-template-rows: repeat(2,minmax(0,1fr));
  grid-template-areas: 'compass map speed' 'altitude map battery'; }
.card, .map-shell { min-width: 0; min-height: 0; overflow: hidden; border: 1px solid #25343a;
  border-radius: 16px; box-shadow: inset 0 1px 0 #ffffff0a, 0 10px 26px #0003; }
.card { box-sizing: border-box; display: flex; flex-direction: column; padding: 16px 18px 10px;
  background: linear-gradient(145deg, #141e23, #10191e 72%); }
.card-compass { grid-area: compass; } .card-speed { grid-area: speed; }
.card-altitude { grid-area: altitude; } .card-battery { grid-area: battery; }
.card-head, .card-foot { display: flex; justify-content: space-between; gap: 8px; }
.eyebrow { color: #a7b6b8; font-size: 10px; font-weight: 800; letter-spacing: .18em; line-height: 1.3; }
.card-index, .card-foot { color: #71868a; font-size: 9px; font-weight: 700; letter-spacing: .12em; }
.metric-row { display: flex; align-items: baseline; gap: 5px; margin-top: 11px; }
.metric-value { font-size: clamp(27px,3.4vh,37px); font-weight: 750; line-height: 1; letter-spacing: -.055em; }
.metric-unit { color: #96a6a5; font-size: 12px; font-weight: 600; }
.chart-wrap { flex: 1; min-height: 0; position: relative; margin: 3px -9px 0 -12px; }
.chart { width: 100%; height: 100%; }
.range-label { position: absolute; left: 4px; z-index: 1; color: #c0ced0; font-size: 11px;
  font-weight: 800; letter-spacing: .04em; line-height: 1; pointer-events: none; white-space: nowrap; }
.range-max { top: 5px; } .range-min { bottom: 17px; }
.compass-wrap { flex: 1; min-height: 0; display: grid; place-items: center; }
.dial { width: min(20.5vh,176px); height: min(20.5vh,176px); min-width: 132px; min-height: 132px;
  position: relative; display: grid; place-items: center; border: 1px solid #405258; border-radius: 50%;
  background: radial-gradient(circle,#18262a 0 43%,transparent 44%),
    repeating-conic-gradient(#486067 0deg 1deg,transparent 1deg 15deg), #111c20;
  box-shadow: 0 0 0 7px #19262b, 0 0 0 8px #304248, inset 0 0 30px #020708; }
.dial:before { content: ''; position: absolute; inset: 18px; border: 1px solid #31474b; border-radius: 50%; }
.dial-direction { position: absolute; color: #849b9d; font-size: 10px; font-weight: 800; }
.dial-n { top: 24px; left: 50%; transform: translateX(-50%); color: #c7f879; }
.dial-e { right: 25px; top: 50%; transform: translateY(-50%); }
.dial-s { bottom: 23px; left: 50%; transform: translateX(-50%); }
.dial-w { left: 25px; top: 50%; transform: translateY(-50%); }
.needle { position: absolute; width: 3px; height: 43%; bottom: 50%; left: calc(50% - 1.5px);
  transform-origin: bottom center; border-radius: 3px;
  background: linear-gradient(#c7f879 0 47%,transparent 48%); filter: drop-shadow(0 0 6px #c7f879); }
.dial-center { z-index: 1; width: 53%; height: 53%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; border: 1px solid #314349; border-radius: 50%;
  background: #101b1f; box-shadow: 0 0 20px #0008; }
.dial-speed { font-size: clamp(28px,4.5vh,45px); line-height: 1; font-weight: 800; letter-spacing: -.075em; }
.dial-unit { color: #84999a; font-size: 9px; font-weight: 800; letter-spacing: .11em; }
.heading-readout { display: flex; justify-content: space-between; color: #9bb0b0;
  font-size: 10px; font-weight: 750; letter-spacing: .08em; }
.heading-value { color: #c7f879; font-size: 13px; }
.map-shell { grid-area: map; position: relative; background: #d8dedb; }
.map-canvas { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; }
.map-top, .map-bottom { position: absolute; z-index: 1100; left: 19px; right: 19px; display: flex;
  justify-content: space-between; pointer-events: none; }
.map-top { top: 19px; align-items: flex-start; } .map-bottom { bottom: 24px; align-items: flex-end; }
.map-title, .map-readout, .map-compass { border: 1px solid #46605c9e; border-radius: 10px;
  background: #101a1ee8; backdrop-filter: blur(10px); }
.map-actions { display: flex; align-items: center; gap: 8px; pointer-events: auto; }
.follow-button { min-height: 35px !important; padding: 0 13px !important; border: 1px solid #46605c;
  border-radius: 10px !important; background: #101a1ee8 !important; color: #a7b6b8 !important;
  font-size: 10px !important; font-weight: 850 !important; letter-spacing: .12em; backdrop-filter: blur(10px); }
.follow-button.following { border-color: #8fbd59; background: #182719ed !important; color: #c7f879 !important; }
.map-title, .map-readout { padding: 9px 12px; }
.map-title .eyebrow { color: #c7f879; }
.map-place { margin-top: 4px; font-size: 20px; font-weight: 750; }
.map-compass { width: 35px; height: 35px; display: grid; place-items: center; color: #c7f879; font-weight: 900; }
.map-readout-label { color: #849d9e; font-size: 9px; font-weight: 800; letter-spacing: .16em; }
.map-readout-value { margin-top: 3px; font-size: 12px; font-weight: 750; }
.gps-grid { flex: 1; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); align-content: center;
  gap: 9px 16px; margin-top: 10px; }
.gps-item { min-width: 0; }
.gps-label { color: #71868a; font-size: 8px; font-weight: 800; letter-spacing: .13em; }
.gps-value { color: #dce8e5; font-size: 12px; font-weight: 750; overflow: hidden; text-overflow: ellipsis; }
.gps-fix { color: #c7f879; }
.vehicle-arrow { color: #17252a; font-size: 30px; line-height: 30px; font-weight: 900;
  filter: drop-shadow(0 1px 1px #fff) drop-shadow(0 0 5px #c7f879); transform-origin: center; }
.statusbar { flex: 0 0 18px; display: flex; justify-content: space-between; gap: 8px;
  color: #71868a; font-size: 9px; font-weight: 750; letter-spacing: .14em; }
@media (orientation: portrait) {
  .dashboard { padding: 14px 14px 10px; }
  .dashboard-grid { grid-template-columns: repeat(2,minmax(0,1fr));
    grid-template-rows: minmax(0,1fr) minmax(0,1fr) minmax(0,2.45fr);
    grid-template-areas: 'compass speed' 'altitude battery' 'map map'; }
  .dial { width: min(14vh,170px); height: min(14vh,170px); }
}
@media (max-width: 650px) {
  .topbar-center, .brand-sub { display: none; }
  .brand-name { font-size: 14px; } .preview-pill { font-size: 8px; }
  .dashboard { padding: 10px; gap: 8px; } .dashboard-grid { gap: 8px; }
  .card { padding: 12px 12px 8px; } .metric-value { font-size: 26px; }
}
"""

Point = tuple[float, float]
TimedValue = tuple[int, float]
MAX_HISTORY = 120
DEFAULT_MAP_CENTER: Point = (52.0693, 19.4803)
DEFAULT_MAP_ZOOM = 6


@dataclass(frozen=True)
class Plot:
    title: str
    unit: str
    color: str
    minimum: float
    maximum: float
    values: tuple[TimedValue, ...]
    decimals: int = 0


@dataclass(frozen=True)
class ScreenState:
    position: Point | None
    path: tuple[Point, ...]
    center: Point
    zoom: int
    speed: float | None
    heading: float | None
    plots: dict[str, Plot]
    gps: dict[str, str]
    follow: bool = True
    view_revision: int = 0


def _point(lat: float, lon: float) -> Point:
    lat, lon = float(lat), float(lon)
    if not (isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('invalid latitude or longitude')
    return lat, lon


def _chart(plot: Plot) -> dict:
    return {
        'animation': False,
        'grid': {'left': 64, 'right': 6, 'top': 8, 'bottom': 21},
        'xAxis': {'type': 'time', 'boundaryGap': False, 'show': False},
        'yAxis': {'type': 'value', 'min': plot.minimum, 'max': plot.maximum,
                  'axisLabel': {'show': False}, 'axisTick': {'show': False},
                  'axisLine': {'show': False},
                  'splitLine': {'lineStyle': {'color': '#34454a', 'type': 'dashed'}}},
        'series': [{'type': 'line', 'data': [list(sample) for sample in plot.values],
                    'smooth': 0.35, 'showSymbol': False,
                    'lineStyle': {'width': 2.5, 'color': plot.color},
                    'areaStyle': {'color': {
                        'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                        'colorStops': [
                            {'offset': 0, 'color': plot.color + '55'},
                            {'offset': 1, 'color': plot.color + '00'},
                        ]}}}],
    }


def _metric(plot: Plot) -> str:
    return f'{plot.values[-1][1]:.{plot.decimals}f}' if plot.values else '—'


def _range_label(label: str, value: float, plot: Plot) -> str:
    return f'{label} {value:.{plot.decimals}f}'


def _position_text(point: Point | None) -> str:
    if point is None:
        return 'WAITING FOR GPS FIX'
    lat, lon = point
    return f'{abs(lat):.5f}° {"N" if lat >= 0 else "S"} / {abs(lon):.5f}° {"E" if lon >= 0 else "W"}'


def _heading_text(degrees: float | None) -> str:
    if degrees is None:
        return '—'
    direction = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')[int((degrees + 22.5) // 45) % 8]
    return f'{degrees:03.0f}°  {direction}'


def _arrow_icon(heading: float) -> str:
    return ("L.divIcon({className: '', iconSize: [30, 30], iconAnchor: [15, 15], "
            f"html: '<div class=\"vehicle-arrow\" style=\"transform:rotate({heading:.1f}deg)\">↑</div>'}})")


class MainScreen:
    """A standalone dashboard; setters update every open browser page.

    GPS samples are timestamped here when received so charts preserve their
    real spacing without exposing timestamps in the dashboard.
    """

    def __init__(self, port: int = 8080) -> None:
        self.port = port
        self._lock = RLock()
        self._state = ScreenState(
            position=None, path=(), center=DEFAULT_MAP_CENTER, zoom=DEFAULT_MAP_ZOOM,
            speed=None, heading=None,
            plots={
                'speed': Plot('SPEED HISTORY', 'km/h', '#e9160f', 0, 10, ()),
                'altitude': Plot('ALTITUDE', 'm', '#71c9d4', 0, 10, (), 1),
            },
            gps={
                'protocol': '—', 'fix': 'NO FIX', 'satellites': '—', 'hdop': '—',
                'rmc': '—', 'nav': '—', 'utc': '—',
            },
        )

    def run(self, *, show: bool = False) -> None:
        ui.run(self.spawn_gui, port=self.port, reload=False, show=show, title='HighwayHub')

    def _set(self, **changes: Any) -> None:
        with self._lock:
            self._state = replace(self._state, **changes)

    def _set_plot(self, name: str, **changes: Any) -> None:
        with self._lock:
            plots = self._state.plots.copy()
            plots[name] = replace(plots[name], **changes)
            self._state = replace(self._state, plots=plots)

    def set_position(self, lat: float, lon: float) -> None:
        self._set(position=_point(lat, lon))

    def set_path(self, points: Iterable[Point]) -> None:
        self._set(path=tuple(_point(*point) for point in points))

    def set_center(self, lat: float, lon: float) -> None:
        point = _point(lat, lon)
        with self._lock:
            self._state = replace(self._state, center=point, view_revision=self._state.view_revision + 1)

    set_view_center = set_center

    def set_zoom(self, zoom: int) -> None:
        if not isinstance(zoom, int) or not 1 <= zoom <= 19:
            raise ValueError('zoom must be an integer from 1 to 19')
        with self._lock:
            self._state = replace(self._state, zoom=zoom, view_revision=self._state.view_revision + 1)

    def set_follow(self, enabled: bool) -> None:
        """Enable or disable keeping the map centered on the latest GPS fix."""
        with self._lock:
            current = self._state
            changes: dict[str, Any] = {'follow': bool(enabled)}
            if enabled and current.position is not None:
                changes.update(center=current.position,
                               view_revision=current.view_revision + 1)
            self._state = replace(current, **changes)

    def set_speed(self, km_per_hour: float) -> None:
        speed = float(km_per_hour)
        if not isfinite(speed) or speed < 0:
            raise ValueError('speed must be non-negative and finite')
        self._set(speed=speed)

    def set_heading(self, degrees: float) -> None:
        heading = float(degrees)
        if not isfinite(heading):
            raise ValueError('heading must be finite')
        self._set(heading=heading % 360)

    def set_plot_title(self, name: str, title: str) -> None:
        if not title.strip():
            raise ValueError('plot title cannot be empty')
        self._set_plot(name, title=title.strip())

    def set_plot_unit(self, name: str, unit: str) -> None:
        self._set_plot(name, unit=unit.strip())

    def set_plot_range(self, name: str, minimum: float, maximum: float) -> None:
        lower, upper = float(minimum), float(maximum)
        if not (isfinite(lower) and isfinite(upper) and lower < upper):
            raise ValueError('minimum must be less than maximum and both must be finite')
        self._set_plot(name, minimum=lower, maximum=upper)

    def set_plot_values(self, name: str, values: Iterable[float]) -> None:
        now = int(time() * 1000)
        samples = tuple((now + index, float(value)) for index, value in enumerate(values))
        if not all(isfinite(value) for _, value in samples):
            raise ValueError('plot values must be finite')
        self._set_plot(name, values=samples)

    @staticmethod
    def _display(value: Any, decimals: int | None = None) -> str:
        if value is None or value == '':
            return '—'
        if decimals is not None:
            try:
                number = float(value)
                return f'{number:.{decimals}f}' if isfinite(number) else '—'
            except (TypeError, ValueError):
                return '—'
        return str(value)

    def update_gps_status(self, status: Any) -> None:
        """Accept the complete ``NmeaParser.status`` object and update GPS UI state."""
        received_at = int(time() * 1000)
        fix = int(getattr(status, 'fix', 0) or 0)
        gps = {
            'protocol': self._display(getattr(status, 'protocol', None)),
            'fix': f'FIX {fix}' if fix else 'NO FIX',
            'satellites': self._display(getattr(status, 'numSats', None)),
            'hdop': self._display(getattr(status, 'horizontalDil', None), 1),
            'rmc': 'VALID' if bool(getattr(status, 'RMCGood', False)) else 'INVALID',
            'nav': 'VALID' if bool(getattr(status, 'NAVGood', False)) else 'INVALID',
            'utc': self._display(getattr(status, 'UTCTime', None)),
        }

        with self._lock:
            current = self._state
            if current.plots['speed'].values:
                received_at = max(received_at, current.plots['speed'].values[-1][0] + 1)
            changes: dict[str, Any] = {'gps': gps}
            if fix:
                try:
                    point = _point(getattr(status, 'lat'), getattr(status, 'lon'))
                    speed = max(0.0, float(getattr(status, 'SOG', 0) or 0))
                    heading = float(getattr(status, 'COG', 0) or 0) % 360
                    altitude = float(getattr(status, 'alt', 0) or 0)
                    if not all(isfinite(value) for value in (speed, heading, altitude)):
                        raise ValueError('non-finite GPS telemetry')
                except (AttributeError, TypeError, ValueError):
                    self._state = replace(current, gps=gps)
                    return

                path = (*current.path, point)[-MAX_HISTORY:]
                plots = current.plots.copy()
                for name, value in (('speed', speed), ('altitude', altitude)):
                    plot = plots[name]
                    values = (*plot.values, (received_at, value))[-MAX_HISTORY:]
                    data_values = [sample[1] for sample in values]
                    lower, upper = min(data_values), max(data_values)
                    padding = max((upper - lower) * 0.15, 5.0 if name == 'speed' else 1.0)
                    plots[name] = replace(plot, values=values,
                                          minimum=lower - padding, maximum=upper + padding)
                changes.update(position=point, path=path, speed=speed,
                               heading=heading, plots=plots)
                if current.follow:
                    changes.update(center=point, zoom=16,
                                   view_revision=current.view_revision + 1)
            self._state = replace(current, **changes)

    def spawn_gui(self) -> None:
        """Build a page; also works as WebguiRoot's subpage callback."""
        ui.dark_mode().enable()
        ui.add_css(CSS)
        initial = self._state

        def plot_card(name: str, number: int) -> tuple[Any, Any, Any, Any, Any, Any]:
            plot = initial.plots[name]
            with ui.element('section').classes(f'card card-{name}'):
                with ui.element('div').classes('card-head'):
                    title = ui.label(plot.title).classes('eyebrow')
                    ui.label(f'{number:02d} / 04').classes('card-index')
                with ui.element('div').classes('metric-row'):
                    value = ui.label(_metric(plot)).classes('metric-value')
                    unit = ui.label(plot.unit).classes('metric-unit')
                with ui.element('div').classes('chart-wrap'):
                    chart = ui.echart(_chart(plot)).classes('chart')
                    maximum = ui.label(_range_label('MAX', plot.maximum, plot)).classes('range-label range-max')
                    minimum = ui.label(_range_label('MIN', plot.minimum, plot)).classes('range-label range-min')
                with ui.element('div').classes('card-foot'):
                    #ui.label('RECENT SAMPLES')
                    ui.label(name.upper())
            return title, value, unit, chart, minimum, maximum

        with ui.element('main').classes('dashboard'):
            with ui.element('header').classes('topbar'):
                with ui.element('div').classes('brand'):
                    ui.label('H').classes('brand-mark')
                    with ui.element('div'):
                        ui.html('HIGHWAY<span>HUB</span>', sanitize=False).classes('brand-name')
                        ui.label('DRIVER DISPLAY').classes('brand-sub')
                ui.label('DRIVE OVERVIEW').classes('topbar-center')
                #with ui.element('div').classes('preview-pill'):
                #    ui.element('span').classes('preview-dot')
                #    ui.label('GPS TELEMETRY')

            with ui.element('div').classes('dashboard-grid'):
                with ui.element('section').classes('card card-compass'):
                    with ui.element('div').classes('card-head'):
                        ui.label('HEADING / SPEED').classes('eyebrow')
                        ui.label('01 / 04').classes('card-index')
                    with ui.element('div').classes('compass-wrap'):
                        with ui.element('div').classes('dial'):
                            for direction in 'NESW':
                                ui.label(direction).classes(f'dial-direction dial-{direction.lower()}')
                            initial_heading = initial.heading or 0.0
                            needle = ui.element('div').classes('needle').style(
                                f'transform: rotate({initial_heading}deg)')
                            with ui.element('div').classes('dial-center'):
                                speed = ui.label(f'{initial.speed:.0f}' if initial.speed is not None else '—').classes('dial-speed')
                                ui.label('KM/H').classes('dial-unit')
                    with ui.element('div').classes('heading-readout'):
                        ui.label('CURRENT HEADING')
                        heading = ui.label(_heading_text(initial.heading)).classes('heading-value')

                plots = {'speed': plot_card('speed', 2)}
                with ui.element('section').classes('map-shell'):
                    map_view = ui.leaflet(center=initial.center, zoom=initial.zoom,
                        options={'zoomControl': False, 'scrollWheelZoom': True, 'touchZoom': True,
                                 'doubleClickZoom': True,
                                 'zoomAnimation': False, 'fadeAnimation': False}).classes('map-canvas')
                    route = map_view.generic_layer(name='polyline', args=[list(initial.path),
                        {'color': '#c7f879', 'weight': 5, 'opacity': 0.9}])
                    marker = map_view.marker(latlng=initial.position or initial.center,
                                             options={'opacity': 1 if initial.position else 0})
                    marker.run_method(':setIcon', _arrow_icon(initial_heading))
                    with ui.element('div').classes('map-top'):
                        with ui.element('div').classes('map-title'):
                            ui.label('MAP OVERVIEW').classes('eyebrow')
                            ui.label('OpenStreetMap').classes('map-place')
                        with ui.element('div').classes('map-actions'):
                            follow = ui.button('FOLLOW', icon='my_location',
                                               on_click=lambda: self.set_follow(True)).props('flat no-caps')
                            follow.classes('follow-button following' if initial.follow else 'follow-button')
                            ui.label('N ↑').classes('map-compass')
                    with ui.element('div').classes('map-bottom'):
                        with ui.element('div').classes('map-readout'):
                            ui.label('CURRENT POSITION').classes('map-readout-label')
                            position = ui.label(_position_text(initial.position)).classes('map-readout-value')
                plots['altitude'] = plot_card('altitude', 3)
                with ui.element('section').classes('card card-battery'):
                    with ui.element('div').classes('card-head'):
                        ui.label('GPS STATUS').classes('eyebrow')
                        ui.label('04 / 04').classes('card-index')
                    gps_labels: dict[str, Any] = {}
                    gps_fields = (
                        ('protocol', 'PROTOCOL'), ('fix', 'FIX QUALITY'),
                        ('satellites', 'SATELLITES'), ('hdop', 'HDOP'),
                        ('rmc', 'RMC'), ('nav', 'NAVIGATION'), ('utc', 'GPS UTC'),
                    )
                    with ui.element('div').classes('gps-grid'):
                        for key, label in gps_fields:
                            with ui.element('div').classes('gps-item'):
                                ui.label(label).classes('gps-label')
                                classes = 'gps-value gps-fix' if key == 'fix' else 'gps-value'
                                gps_labels[key] = ui.label(initial.gps[key]).classes(classes)

            with ui.element('footer').classes('statusbar'):
                ui.label('HIGHWAYHUB / DRIVER DISPLAY')
                ui.label('TELEMETRY VALUES CAN BE UPDATED')

            previous = initial

            def map_view_changed(event: Any) -> None:
                """Stop following when the resulting map view differs from the tracked view."""
                with self._lock:
                    current = self._state
                    if not current.follow:
                        return
                    center = event.args.get('center', map_view.center)
                    zoom = int(event.args.get('zoom', map_view.zoom))
                    latitude_delta = abs(float(center[0]) - current.center[0])
                    longitude_delta = abs(float(center[1]) - current.center[1])
                    if latitude_delta > 1e-7 or longitude_delta > 1e-7 or zoom != current.zoom:
                        self._state = replace(current, follow=False)

            map_view.on('map-moveend', map_view_changed)
            map_view.on('map-zoomend', map_view_changed)

            def refresh() -> None:
                nonlocal previous
                current = self._state
                if current == previous or not map_view.is_initialized:
                    return
                if current.view_revision != previous.view_revision:
                    map_view.run_map_method('setView', current.center, current.zoom)
                if current.position != previous.position:
                    if current.position is not None:
                        marker.move(*current.position)
                        marker.run_method('setOpacity', 1)
                    position.set_text(_position_text(current.position))
                if current.path != previous.path:
                    route.run_method('setLatLngs', list(current.path))
                if current.speed != previous.speed:
                    speed.set_text(f'{current.speed:.0f}')
                if current.heading != previous.heading:
                    heading.set_text(_heading_text(current.heading))
                    displayed_heading = current.heading or 0.0
                    needle.style(f'transform: rotate({displayed_heading}deg)')
                    marker.run_method(':setIcon', _arrow_icon(displayed_heading))
                if current.gps != previous.gps:
                    for key, label in gps_labels.items():
                        label.set_text(current.gps[key])
                if current.follow != previous.follow:
                    if current.follow:
                        follow.classes(add='following')
                    else:
                        follow.classes(remove='following')
                for name, plot in current.plots.items():
                    if plot == previous.plots[name]:
                        continue
                    title, value, unit, chart, minimum, maximum = plots[name]
                    title.set_text(plot.title)
                    value.set_text(_metric(plot))
                    unit.set_text(plot.unit)
                    minimum.set_text(_range_label('MIN', plot.minimum, plot))
                    maximum.set_text(_range_label('MAX', plot.maximum, plot))
                    chart.options.clear()
                    chart.options.update(_chart(plot))
                    chart.update()
                previous = current

            ui.timer(0.25, refresh, immediate=False)


if __name__ == '__main__':
    MainScreen().run()
