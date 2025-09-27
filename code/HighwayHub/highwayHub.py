import time

from DataSource import InformationCenter, GpsHandler
from LoggingSetup import getLogger


logger = getLogger(__name__)

class HighwayHub:
    def __init__(self):
        self.printMotd()
        self.ic = InformationCenter()
        self.gpsHandler = GpsHandler()

    def printMotd(self):
        logger.debug("Welcome, to HighwayHub")
        logger.info("Welcome, to HighwayHub")
        logger.warning("Welcome, to HighwayHub")
        logger.error("Welcome, to HighwayHub")
        logger.critical("Welcome, to HighwayHub")

    def run(self):
        while(1):
            time.sleep(1)