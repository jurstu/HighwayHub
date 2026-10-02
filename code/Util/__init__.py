from logging_setup import get_logger

class EmptyClass:
    def __init__(self):
        pass



class Signal:
    def __init__(self, name):
        self.name = name
        self.receivers = []

    def addReceiver(self, call):
        self.receivers.append(call)

    def trigger(self, value=None):
        for rx in self.receivers:
            try:
                if value is not None:
                    rx(value)
                else:
                    rx()
            except Exception as ex:
                logger = get_logger("Signal Class")
                logger.error(f"error at signal {self.name} {ex}")

def printMotd():
    logger = get_logger("HIGHWAY HUB")
    logger.debug("Welcome, to HighwayHub")
    logger.info("Welcome, to HighwayHub")
    logger.warning("Welcome, to HighwayHub")
    logger.error("Welcome, to HighwayHub")
    logger.critical("Welcome, to HighwayHub")

all = ["EmptyClass", "printMotd"]