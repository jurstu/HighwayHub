import numpy as np
from Util import Signal
from LoggingSetup import getLogger
import copy

logger = getLogger(__name__)



class WaypointAnalyzer:
    def __init__(self):
        self.lastWaypoints = []
        self.newElevationDataSignal = Signal("new elevation data")

    def feedPoint(self, data):

        if(len(self.lastWaypoints) != 0 and data.UTCTime == self.lastWaypoints[-1].UTCTime):
            #logger.warning("new waypoint has got the same time as the last")
            return
        
        
        
        self.lastWaypoints.append(copy.copy(data))
        self.lastWaypoints = self.lastWaypoints[-300:] # leave 300 last datapoints

        positions = []
        speeds = []
        alts = []

        for dataPoint in self.lastWaypoints:
            positions.append([dataPoint.lat, dataPoint.lon])
            speeds.append([dataPoint.SOG, dataPoint.COG])
            alts.append(dataPoint.alt)

        
        self.newElevationDataSignal.trigger(alts)
        


