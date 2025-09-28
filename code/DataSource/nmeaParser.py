import pynmea2
from LoggingSetup import getLogger
import datetime
import time
from Util import EmptyClass, Signal

logger = getLogger(__name__)


class NmeaParser:
    def __init__(self):
        self.status = EmptyClass()
        self.status.protocol = "NMEA"
        self.status.lat = 0
        self.status.lon = 0
        self.status.RMCGood = 0
        self.status.UTCTime = datetime.datetime.now()

        self.status.NAVGood = 0
        self.status.SOG = 0
        self.status.COG = 0

        self.status.fix = 0
        self.status.numSats = 0
        self.status.alt = 0
        self.status.horizontalDil = 0

        self.buffer = ""
        self.suffixList = {
            "GGA": self.msgGGAHandler,
            "VTG": self.msgVTGHandler,
            "RMC": self.msgRMCHandler,
        }
        self.lastRxTime = 0
        self.newPositionSignal = Signal("new position signal")

    def newMsg(self, data):
        try:
            self.buffer += data            
            self.parse()
        except:
            pass

    def __repr__(self):
        output = "sats={:02d}, lat={:02.4f}, lat={:02.4f}, time={}".format(self.status.numSats, self.status.lat, self.status.lon, self.status.UTCTime.strftime("%Y-%m-%d %H:%M"))
        return output

    def getStatus(self):
        return (time.time() - self.lastRxTime) < 2

    def updateStatus(self):
        self.lastRxTime = time.time()

    def parse(self):
        while True:
            # Look for start and end of a sentence
            start_idx = self.buffer.find("$")
            if start_idx == -1:
                # No start of sentence found
                self.buffer = ""
                break

            end_idx = self.buffer.find("\r\n", start_idx)
            if end_idx == -1:
                # No complete sentence yet
                self.buffer = self.buffer[start_idx:]  # Discard data before $
                break

            sentence = self.buffer[start_idx:end_idx]
            self.buffer = self.buffer[end_idx + 2 :]  # Remove processed sentence
            try:
                msg = pynmea2.parse(sentence)
                # logger.debug(repr(msg))
                idd = msg.identifier()[:-1]
                for k in self.suffixList:
                    if idd.endswith(k):
                        self.suffixList[k](msg)
                        self.lastRxTime = time.time()
                        break

            except pynmea2.ParseError as e:
                logger.warning(e)

    def msgGGAHandler(self, message):

        # logger.info("GGA Message" + repr(message))

        self.status.fix = message.gps_qual

        if self.status.fix:
            self.status.numSats = int(message.num_sats)
            self.status.alt = message.altitude
            self.status.horizontalDil = message.horizontal_dil
            self.status.lat = self.dmmToDecimal(message.lat, message.lat_dir)
            self.status.lon = self.dmmToDecimal(message.lon, message.lon_dir)

        self.newPositionSignal.trigger(self.status)



    def msgVTGHandler(self, message):
        pass
        # logger.info("VTG Message")

    def dmmToDecimal(self, coord_str, direction):
        if not coord_str:
            return None

        deg_len = 2 if direction in ["N", "S"] else 3
        degrees = float(coord_str[:deg_len])
        minutes = float(coord_str[deg_len:])
        decimal = degrees + (minutes / 60)

        if direction in ["S", "W"]:
            decimal *= -1

        return decimal

    def msgRMCHandler(self, message):
        # logger.info("RMC Message")
        # logger.info(message.render())
        # logger.info(repr(message))
        RMCGood = message.status == "A"  # A-ctive, V-oid
        self.status.RMCGood = RMCGood
        if RMCGood:
            lat = self.dmmToDecimal(message.lat, message.lat_dir)
            lon = self.dmmToDecimal(message.lon, message.lon_dir)
            timedate = message.timestamp
            datedate = message.datestamp
            UTC = datetime.datetime.combine(datedate, timedate)
            self.status.UTC = UTC
            self.status.lat = lat
            self.status.lon = lon

        NAVGood = message.nav_status == "V"  # V-alid
        self.status.NAVGood = NAVGood
        if NAVGood:
            self.status.SOG = message.spd_over_grnd * 1.852  # knots per hour  ----> km per hour
            self.status.COG = message.true_course if message.true_course is not None else 0


if __name__ == "__main__":
    from Util import SerialGuard
    import time

    nmeaParser = NmeaParser()
    sg = SerialGuard([nmeaParser.newMsg], "/dev/ttyACM0")

    while 1:
        time.sleep(3)