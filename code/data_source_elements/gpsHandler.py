import time
from collections import deque
import copy

from .serialGuard import SerialGuard
from .nmeaParser import NmeaParser
from Util import Signal

from logging_setup import get_logger

logger = get_logger(__name__)

class GpsHandler:
    def __init__(self):
        self.nmeaParser = NmeaParser()
        self.nmeaParser.newPositionSignal.addReceiver(self.newPositionAvailable)
        self.newPositionSignal = Signal("new position signal")
        self.sg = SerialGuard("/dev/ttyUSB0", 9600) # TODO maybe do a udev for port path and some autobauding, idk
        self.sg.new_data_callback_signal.addReceiver(self.nmeaParser.newMsg)

    def newPositionAvailable(self, data):
        self.newPositionSignal.trigger(self.nmeaParser)
        if(data.fix == 0):
            logger.warning(f"waiting for fix")
        else:
            logger.info(f"new position {self.nmeaParser}")
