import json
import logging
from types import MethodType

import numpy as np


def get_logger(name, level=logging.DEBUG):
    LOGFORMAT = (
        " %(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | "
        "%(name)-30s | %(log_color)s%(message)s%(reset)s"
    )

    from colorlog import ColoredFormatter

    formatter = ColoredFormatter(LOGFORMAT)

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(level)

    if not log.handlers:
        log.addHandler(stream)

    def json_default(value):
        if isinstance(value, np.ndarray):
            return value.tolist()

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.bool_):
            return bool(value)

        raise TypeError(
            f"Object of type {type(value).__name__} "
            "is not JSON serializable"
        )

    def json_log(self, obj, level=logging.INFO, **kwargs):
        kwargs.setdefault("indent", 4)
        kwargs.setdefault("default", json_default)

        self.log(
            level,
            "\n" + json.dumps(obj, **kwargs),
        )

    log.json = MethodType(json_log, log)

    return log