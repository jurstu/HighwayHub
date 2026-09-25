import json
import time
import os
import ipaddress
import platform

import math
import glob
from pathlib import Path
import platform


def listOfBytes(data):
    return ["{:02X} ".format(x) for x in list(data)]

def limit(val, minVal, maxVal):
    return min(max(minVal, val), maxVal)


def map(value, minIn, maxIn, minOut, maxOut):
    out = ((value - minIn) / (maxIn - minIn)) * (maxOut - minOut) + minOut
    return out


def degToRad(value):
    return value * math.pi / 180


def radToDeg(value):
    return value * 180 / math.pi


def inRange(value, min, max):
    return (min <= value) and (value <= max)


class EmptyClass:
    def __init__(self):
        pass


def getGlobFromPath(path):
    return glob.glob(path)


def createDir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def isIPValid(ip):
    output = False
    try:
        ipaddress.ip_address(ip)
        output = True
    except:
        output = False
    return output




def getSerialPortsAvailable():
    devices = os.listdir("/dev/")
    outList = []
    exclusiveTTYprefixes = ["ttym", "ttyA", "ttyUSB"]

    for dev in devices:
        for prefix in exclusiveTTYprefixes:
            if dev.startswith(prefix):
                outList.append(dev)
    return outList


def getJson(path):
    f = open(path, "r")
    d = f.read()
    f.close()
    return json.loads(d)


def saveJson(path, dic):
    f = open(path, "w")
    f.write(json.dumps(dic, indent=4))
    f.close()


def isThisX86():
    plat = platform.uname()[4]
    return plat == "x86_64"