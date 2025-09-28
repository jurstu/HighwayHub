import time

from .serialGuard import SerialGuard
from .nmeaParser import NmeaParser
from .informationCenter import InformationCenter

from LoggingSetup import getLogger

logger = getLogger(__name__)

class GpsHandler:
    def __init__(self):
        
        self.ic = InformationCenter()
        self.params = self.ic.getValue("PARAMS")
        self.nmeaParser = NmeaParser()
        self.nmeaParser.newPositionSignal.addReceiver(self.newPositionAvailable)
        self.sg = SerialGuard([self.nmeaParser.newMsg], self.params["gpsPortPath"], self.params["gpsPortSpeed"])


    def newPositionAvailable(self, data):
        if(data.fix == 0):
            logger.warning(f"waiting for fix")
        else:
            logger.info(f"new position {self.nmeaParser}")

        self.ic.setValue("last gps update ts", time.time())

