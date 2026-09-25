"""Run HighwayHub with a live, circular GPS demo."""

from collections import deque
from math import cos, pi, sin
import time

from webgui import WebguiRoot


CENTER = (52.2297, 21.0122)  # Warsaw
LAT_RADIUS = 0.022
LON_RADIUS = 0.036
LAP_SECONDS = 24.0
UPDATE_SECONDS = 0.1
TRACE_LENGTH = 10


def circle_position(elapsed: float) -> tuple[float, float]:
    angle = 2 * pi * elapsed / LAP_SECONDS
    return (
        CENTER[0] + LAT_RADIUS * cos(angle),
        CENTER[1] + LON_RADIUS * sin(angle),
    )


def main() -> None:
    webgui = WebguiRoot()
    screen = webgui.main_screen
    screen.set_center(*CENTER)

    # Start with a short visible trail; keep only the most recent 10 fixes.
    trail = deque(
        (circle_position(-step * UPDATE_SECONDS) for step in range(TRACE_LENGTH - 1, -1, -1)),
        maxlen=TRACE_LENGTH,
    )
    screen.set_position(*trail[-1])
    screen.set_path(trail)
    webgui.run()

    start = time.monotonic()
    tick = 1
    try:
        while True:
            time.sleep(max(0, start + tick * UPDATE_SECONDS - time.monotonic()))
            position = circle_position(tick * UPDATE_SECONDS)
            trail.append(position)
            screen.set_position(*position)
            screen.set_path(trail)
            tick += 1
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
