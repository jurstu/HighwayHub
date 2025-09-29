from .jpegDoubleCapture import JpegDoubleCapture
from DataSource import InformationCenter



class VideoManager:
    def __init__(self):
        self.ic = InformationCenter()
        self.params = self.ic.getValue("PARAMS")
        self.videoParams = self.params["firstVideoSettings"]
        
        self.jdc = JpegDoubleCapture(self.videoParams["ww"], self.videoParams["hh"], self.videoParams["cameraPath"])
        