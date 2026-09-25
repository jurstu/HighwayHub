import time


class FrequencyCounter:
    def __init__(self, startOnReset=False):
        if startOnReset:
            self.start = time.time()
        self.startOnReset = startOnReset
        self.cnt = 0
        self.lastTriggerTime = 0

    def __str__(self):
        return "{: 2.2f}".format(self.getFreq())

    def isDue(self, freq):
        return self.getFreq() < freq

    def trigger(self):
        if not hasattr(self, "start"):
            self.start = time.time()
        self.lastTriggerTime = time.time()
        self.cnt += 1

    def getFreq(self):
        if not hasattr(self, "start"):
            self.start = time.time() - 0.0001

        tt = time.time()
        dt = tt - self.start
        if dt != 0:
            out = self.cnt / dt
        else:
            out = 0

        return out

    def getTimeSinceLastTrigger(self):
        return time.time() - self.lastTriggerTime

    def reset(self):
        self.cnt = 0
        if self.startOnReset:
            self.start = time.time()
        else:
            if hasattr(self, "start"):
                del self.start


if __name__ == "__main__":
    fc = FrequencyCounter()
    i = 0
    while 1:
        i += 1
        fc.trigger()
        time.sleep(0.1)
        if i > 10:
            i = 0
            fc.reset()
            fc.trigger()