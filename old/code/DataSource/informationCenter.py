from Util import getJson, saveJson
from LoggingSetup import getLogger

logger = getLogger(__name__)

# singleton


class InformationCenter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InformationCenter, cls).__new__(cls)

            # init part
            cls._instance.theDict = {}
            cls._instance.initValues()
        return cls._instance

    def initValues(self):
        logger.info("init values at information center")

        self.setValue("PARAMS", getJson("./params.json"))
        self.setValue("car-centered", True)
        self.setValue("last gps update ts", 0)
        self.setValue("recentPositionsList", [])
    

    def getValue(self, valueName, defaultValue=None):
        if valueName in self.theDict:
            return self.theDict[valueName]
        else:
            logger.error("non-existent value requested: " + str(valueName))
            return defaultValue

    def setValue(self, valueName, value):
        if not (valueName in self.theDict):
            logger.warning(f"Value {valueName} hasn't been set yet, setting it to {value}")
        self.theDict[valueName] = value

        if valueName == "PARAMS":
            logger.debug("saving params")
            saveJson("./params.json", self.theDict["PARAMS"])