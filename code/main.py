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
        self.gps = GpsHandler()
        self.gps.newPositionSignal.addReceiver(self.new_gps)

        self.webgui = WebguiRoot()
        self.webgui.run()

    def new_gps(self, position):
        logger.info(f"new gps: {position}")
        if(position.status.fix != 0):
            lat = position.status.lat
            lon = position.status.lon
            st = position.status
            self.webgui.main_screen.set_center(lat, lon)
            self.webgui.main_screen.set_position(lat, lon)
            self.webgui.main_screen.set_speed(st.SOG)
            self.webgui.main_screen.set_heading(st.COG)
            #self.webgui.main_screen.set



def main() -> None:
    printMotd()
    mainClass()

    while(1):
        time.sleep(5)

if __name__ == '__main__':
    main()


