import json

from DataSource import InformationCenter
from LoggingSetup import getLogger


logger = getLogger(__name__)

class RadarWatcher:
    def __init__(self):
        self.ic = InformationCenter()
        self.ic.setValue("RadarWatcherObject", self)
        try:
            with open("assets/canard_detailed_data.json", "r") as f:
                data = json.load(f)
            
        except Exception as e:
            logger.warning(f"couldn't load canard data {e}")
            data = {}
        
        self.detectionEntryRadius = 1000
        



