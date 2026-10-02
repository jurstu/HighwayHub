"""Run HighwayHub with a live, circular GPS demo."""

from collections import deque
from math import cos, pi, sin
import time

from webgui import WebguiRoot






def main() -> None:
    webgui = WebguiRoot()
    webgui.run()

    start = time.monotonic()
    tick = 1
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
