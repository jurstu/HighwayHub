import logging


def getLogger(name, level=logging.DEBUG):
    LOG_LEVEL = level
    LOGFORMAT = " %(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | %(name)-30s | %(log_color)s%(message)s%(reset)s"
    from colorlog import ColoredFormatter

    logging.root.setLevel(LOG_LEVEL)
    formatter = ColoredFormatter(LOGFORMAT)
    stream = logging.StreamHandler()
    stream.setLevel(LOG_LEVEL)
    stream.setFormatter(formatter)
    log = logging.getLogger(name)
    log.setLevel(LOG_LEVEL)
    log.addHandler(stream)

    return log