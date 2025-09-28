import sys
import io
from contextlib import redirect_stdout
from LoggingSetup import getLogger


class StdoutInterceptor(io.StringIO):
    def __init__(self, loggerName, writtenCb):
        super().__init__()
        self.logger = getLogger(loggerName)
        self.writtenCb = writtenCb

    def write(self, s):
        if s.strip():  # skip empty lines
            self.logger.info(s.strip())
            self.writtenCb()

    def flush(self):
        pass  # required for compatibility