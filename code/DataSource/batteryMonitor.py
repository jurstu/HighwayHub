import smbus
import time
import os

from DataSource import InformationCenter
from LoggingSetup import getLogger
from Util import EmptyClass, Signal


logger = getLogger(__name__)

ADDR = 0x2d
LOW_VOL = 3150 #mV




class BatteryMonitor:
    def __init__(self):
        self.ic = InformationCenter()
        self.bus = smbus.SMBus(1)
        self.state = EmptyClass()
        self.state.chargingStatus = "Idle state"
        self.state.vbusVoltage = 0
        self.state.vbusCurrent = 0

        self.state.battCurrent  = 0 
        self.state.battVoltage  = 0
        self.state.battPercent  = 0
        self.state.remCapacity  = 0
        self.state.timeToEmpty  = 0
        self.state.timeToFull   = 0
        self.state.cellVolts = [0, 0, 0, 0]
        self.state.lastUpdateTs = 0

        self.battDataUpdateSignal = Signal("Battery update signal")


    def status(self):
        pass

    def updateData(self):
        try:
            data = self.bus.read_i2c_block_data(ADDR, 0x02, 0x01)
            if(data[0] & 0x40):
                self.state.chargingStatus = "Fast Charging state"
            elif(data[0] & 0x80):
                self.state.chargingStatus = "Charging state"
            elif(data[0] & 0x20):
                self.state.chargingStatus = "Discharge state"
            else:
                self.state.chargingStatus = "Idle state"
        except:
            logger.warning("didn't manage to read charging state")



        try:
            data = self.bus.read_i2c_block_data(ADDR, 0x10, 0x06)
            self.state.vbusVoltage = int(data[0] | data[1] << 8)
            self.state.vbusCurrent = int(data[2] | data[3] << 8)
        except:
            logger.warning("didn't manage to read VBUS stats")

        try:
            data = self.bus.read_i2c_block_data(ADDR, 0x20, 0x0C)
            self.state.battVoltage = int(data[0] | data[1] << 8)
            current = (data[2] | data[3] << 8)
            if(current > 0x7FFF):
                current -= 0xFFFF
            self.state.battCurrent = current
            self.state.battPercent = int(data[4] | data[5] << 8)
            self.state.remCapacity = int(data[6] | data[7] << 8)
            
            if(current < 0):
                self.state.timeToEmpty = int(data[8] | data[9] << 8)
            else:
                self.state.timeToFull = int(data[10] | data[11] << 8)
        except:
            logger.warning("didn't manage to read battery stats")

        try:
            data = self.bus.read_i2c_block_data(ADDR, 0x30, 0x08)
            V1 = (data[0] | data[1] << 8)
            V2 = (data[2] | data[3] << 8)
            V3 = (data[4] | data[5] << 8)
            V4 = (data[6] | data[7] << 8)

            self.state.cellVolts[1-1] = V1
            self.state.cellVolts[2-1] = V2
            self.state.cellVolts[3-1] = V3
            self.state.cellVolts[4-1] = V4
        except:
            logger.warning("didn't manage to read cell voltages")



        self.battDataUpdateSignal.trigger(self.state)













#print("If charged, the system can be powered on again")
## write 0x55 to 0x01 register of 0x2d Address device
#os.popen("i2cset -y 1 0x2d 0x01 0x55")
#os.system("sudo poweroff")