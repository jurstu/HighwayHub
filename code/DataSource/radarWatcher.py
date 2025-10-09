import json

from DataSource import InformationCenter
from LoggingSetup import getLogger
import numpy as np

logger = getLogger(__name__)

class RadarWatcher:
    def __init__(self):
        self.ic = InformationCenter()
        self.ic.setValue("RadarWatcherObject", self)
        try:
            with open("assets/canard_detailed_data.json", "r") as f:
                self.data = json.load(f)
            
        except Exception as e:
            logger.warning(f"couldn't load canard data {e}")
            self.data = {}
        
        self.loadIntererstingPoints()

        self.detectionEntryRadius = 1000
        

    def loadIntererstingPoints(self):
        self.points = {}
        for k, v in self.data.items():
            if("urzadzenie" in v):
                data = {
                    "lat": v["lat"],
                    "lon": v["lon"],
                    "type": v["urzadzenie"]["rodzajPomiaru"],
                }
                self.points[k] = data
        
    def calculateDistance(self, lat1, lon1, lat2, lon2):
        R = 6371000.0  # mean Earth radius [m]
        # convert degrees to radians
        lat1 = np.radians(lat1)
        lon1 = np.radians(lon1)
        lat2 = np.radians(lat2)
        lon2 = np.radians(lon2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c

    def getDistances(self, position):
        logger.info("checking distances")
        dsts = {}
        inRange = {}
        for k, v in self.points.items():
            dsts[k] = self.calculateDistance(position[0], position[1], v["lat"], v["lon"])
            if(dsts[k] < self.detectionEntryRadius):
                logger.info("point in range")
        
        return dsts



