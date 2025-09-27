import time
from threading import Thread
import serial
from LoggingSetup import getLogger

logger = getLogger(__name__)


class SerialGuard:
    def __init__(self, dataReceiveCallbacks, portName="/dev/ttyUSB0", portBaud=115200, raw=False):
        self.raw = raw
        self.portName = portName
        self.portBaud = portBaud
        self.receiveCallbacks = dataReceiveCallbacks
        self.end = False
        self.start()

    def start(self):
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.end = True

    def run(self):
        while not self.end:
            try:
                self.serial = serial.Serial(self.portName, self.portBaud)
            except Exception as e:
                logger.error("couldn't open serial: " + str(e))
                time.sleep(1)
                continue

            while not self.end:
                try:
                    data = self.serial.read(self.serial.in_waiting)
                except Exception as e:
                    logger.error("error while reading data from serial" + str(e))
                    if self.serial.is_open:
                        self.serial.close()
                        break
                if len(data) <= 0:
                    continue

                if self.raw == False:
                    try:
                        strdata = data.decode("utf-8")
                        for cb in self.receiveCallbacks:
                            cb(strdata)
                        time.sleep(0.01)
                    except Exception as e:
                        logger.warning("probably utf- conversion error: " + str(e))
                        logger.warning("data was: " + str(data))
                else:
                    for cb in self.receiveCallbacks:
                        cb(data)
                time.sleep(0.1)
            self.serial.close()

        self.serial.close()

    def sendData(self, data, raw=False):
        if hasattr(self, "serial"):
            if self.serial.is_open:
                if raw == False and self.raw == False:
                    self.serial.write((str(data)).encode("utf-8"))
                else:
                    self.serial.write(data)
            else:
                logger.warning("uart isn't open, not sending this data: " + str(data))
        else:
            logger.warning("uart isn't open, not sending this data: " + str(data))

    def isSerialOpen(self):
        if hasattr(self, "serial"):
            if self.serial.is_open:
                return True
            else:
                return False
        else:
            return False


if __name__ == "__main__":

    def here(asdf):
        logger.info("data from serial" + str(asdf))

    a = SerialGuard([here], "/dev/ttyUSB0", 9600)

    while 1:
        time.sleep(1)
        a.sendData("qwer")