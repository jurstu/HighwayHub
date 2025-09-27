from LoggingSetup import getLogger

logger = getLogger(__file__)

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
                logger.error("error at signalling", ex)