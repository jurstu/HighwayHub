"""Run HighwayHub with a live, circular GPS demo."""

from collections import deque
from math import cos, pi, sin
import time
from Util import printMotd

from webgui import WebguiRoot
from data_source_elements import GpsHandler

from logging_setup import get_logger

logger = get_logger(__name__)





class mainClass:
    def __init__(self):
        self.gps = GpsHandler([self.new_gps])
        self.webgui = WebguiRoot()
        self.webgui.run()

    def new_gps(self, position):
        logger.info(f"new gps: {position}")


def main() -> None:
    printMotd()
    mainClass()

    while(1):
        time.sleep(5)

if __name__ == '__main__':
    main()


