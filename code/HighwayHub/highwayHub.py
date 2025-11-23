import time
import numpy as np


from DataSource import InformationCenter, GpsHandler, BatteryMonitor, RadarWatcher, WaypointAnalyzer
from LoggingSetup import getLogger
from UiGen import UiGen
from Video import VideoManager
from Util import isThisX86
from Util import EmptyClass

logger = getLogger(__name__)

class HighwayHub:
    def __init__(self):
        self.printMotd()
        self.ic = InformationCenter()
        self.gpsHandler = GpsHandler()
        self.radarWatcher = RadarWatcher()
        self.waypointAnalyzer = WaypointAnalyzer()


        if(isThisX86()):
            pass
        else:
            self.battMonitor = BatteryMonitor()
        
        self.videoManager = VideoManager()

        self.uiGen = UiGen()
        self.uiGen.run()

        self.gpsHandler.nmeaParser.newPositionSignal.addReceiver(self.uiGen.updateGpsData)
        self.gpsHandler.nmeaParser.newPositionSignal.addReceiver(self.waypointAnalyzer.feedPoint)
        self.waypointAnalyzer.newElevationDataSignal.addReceiver(self.uiGen.updateElevationData)
        if(isThisX86()):
            pass
        else:
            self.battMonitor.battDataUpdateSignal.addReceiver(self.uiGen.updateBatteryData)
        #self.videoManager.jdc.newJpegSignal.addReceiver(self.uiGen.videoPage.newJpegImage)


    def printMotd(self):
        logger.debug("Welcome, to HighwayHub")
        logger.info("Welcome, to HighwayHub")
        logger.warning("Welcome, to HighwayHub")
        logger.error("Welcome, to HighwayHub")
        logger.critical("Welcome, to HighwayHub")

    def run(self):
        #a = EmptyClass()
        #a.lat = 52
        #a.lon = 21
        #a.alt = 100
        #a.COG = 30
        #a.fix = 1

        i = 0
        while(1):
            if(isThisX86()):
                pass
            else:
                self.battMonitor.updateData()
                #self.uiGen.updateGpsData(a)

            time.sleep(1)
            #time.sleep(0.1)
            #logger.info("changing position")
            #a.lat = 52 + 0.3*np.sin((i/100)*np.pi)
            #a.lon = 21 + 0.3*np.cos((i/100)*np.pi)
            #a.COG = int(-i*180/100)
            #a.fix = (i//10) % 2
            #i += 1
                
            