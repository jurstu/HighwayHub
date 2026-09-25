import time

from DataSource import InformationCenter, GpsHandler, BatteryMonitor, RadarWatcher
from LoggingSetup import getLogger
from UiGen import UiGen
from Video import VideoManager
from Util import isThisX86

logger = getLogger(__name__)

class HighwayHub:
    def __init__(self):
        self.printMotd()
        self.ic = InformationCenter()
        self.gpsHandler = GpsHandler()
        self.radarWatcher = RadarWatcher()


        if(isThisX86()):
            pass
        else:
            self.battMonitor = BatteryMonitor()
        
        self.videoManager = VideoManager()

        self.uiGen = UiGen()
        self.uiGen.run()

        self.gpsHandler.nmeaParser.newPositionSignal.addReceiver(self.uiGen.updateGpsData)
        if(isThisX86()):
            pass
        else:
            self.battMonitor.battDataUpdateSignal.addReceiver(self.uiGen.updateBatteryData)
        self.videoManager.jdc.newJpegSignal.addReceiver(self.uiGen.videoPage.newJpegImage)


    def printMotd(self):
        logger.debug("Welcome, to HighwayHub")
        logger.info("Welcome, to HighwayHub")
        logger.warning("Welcome, to HighwayHub")
        logger.error("Welcome, to HighwayHub")
        logger.critical("Welcome, to HighwayHub")

    def run(self):
        while(1):
            if(isThisX86()):
                pass
            else:
                self.battMonitor.updateData()
            time.sleep(1)