import logging
from colorlog import ColoredFormatter


def getLogger(name, level=logging.DEBUG):
    LOG_LEVEL = level
    LOGFORMAT = (
        " %(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | "
        "%(name)-30s | %(log_color)s%(message)s%(reset)s"
    )

    LOG_COLORS = {
        'DEBUG':    'purple',   # only DEBUG changed to purple
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'bold_red',
    }

    logging.root.setLevel(LOG_LEVEL)
    formatter = ColoredFormatter(LOGFORMAT, log_colors=LOG_COLORS)
    stream = logging.StreamHandler()
    stream.setLevel(LOG_LEVEL)
    stream.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(LOG_LEVEL)
    log.addHandler(stream)

    return log