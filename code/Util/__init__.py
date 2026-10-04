from logging_setup import get_logger

from .signal import Signal

class EmptyClass:
    def __init__(self):
        pass




def printMotd():
    logger = get_logger("HIGHWAY HUB")
    logger.debug("Welcome, to HighwayHub")
    logger.info("Welcome, to HighwayHub")
    logger.warning("Welcome, to HighwayHub")
    logger.error("Welcome, to HighwayHub")
    logger.critical("Welcome, to HighwayHub")

all = ["EmptyClass", "printMotd"]