import time
from collections import deque
import copy

from .serialGuard import SerialGuard
from .nmeaParser import NmeaParser

from logging_setup import get_logger

logger = get_logger(__name__)

class GpsHandler:
    def __init__(self, callbacks):
        self.nmeaParser = NmeaParser()
        self.nmeaParser.newPositionSignal.addReceiver(self.newPositionAvailable)
        self.sg = SerialGuard([self.nmeaParser.newMsg], "/dev/ttyUSB0", 115200) # TODO maybe do a udev for port path and some autobauding, idk

    def newPositionAvailable(self, data):
        if(data.fix == 0):
            logger.warning(f"waiting for fix")
        else:
            logger.info(f"new position {self.nmeaParser}")
