import time

from DataSource import InformationCenter, GpsHandler, BatteryMonitor
from LoggingSetup import getLogger
from UiGen import UiGen


logger = getLogger(__name__)

class HighwayHub:
    def __init__(self):
        self.printMotd()
        self.ic = InformationCenter()
        self.gpsHandler = GpsHandler()
        self.battMonitor = BatteryMonitor()
        
        self.uiGen = UiGen()
        self.uiGen.run()
        self.gpsHandler.nmeaParser.newPositionSignal.addReceiver(self.uiGen.updateGpsData)
        self.battMonitor.battDataUpdateSignal.addReceiver(self.uiGen.updateBatteryData)


    def printMotd(self):
        logger.debug("Welcome, to HighwayHub")
        logger.info("Welcome, to HighwayHub")
        logger.warning("Welcome, to HighwayHub")
        logger.error("Welcome, to HighwayHub")
        logger.critical("Welcome, to HighwayHub")

    def run(self):
        while(1):
            self.battMonitor.updateData()
            time.sleep(1)