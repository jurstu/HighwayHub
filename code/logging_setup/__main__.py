from logging_setup import get_logger

logger = get_logger("loggingSetup package")

logger.debug("debug message")
logger.info("info message")
logger.warning("warning message")
logger.error("error message")
logger.critical("critical message")