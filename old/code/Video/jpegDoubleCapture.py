import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import numpy as np
import cv2
from threading import Thread
from Util import Signal
from LoggingSetup import getLogger

logger = getLogger(__name__)

Gst.init(None)

class JpegDoubleCapture:
    def __init__(self, ww, hh, cameraPath):
        self.ww = ww
        self.hh = hh
        self.cameraPath = cameraPath
        self.www = ww
        self.hhh = hh
        self.newJpegSignal = Signal("new Jpeg signal")
        self.newRawSignal = Signal("new Raw signal")


        # Create the pipeline
        
        self.pipeline_description = f"""
            v4l2src device={cameraPath} ! image/jpeg,width={ww},height={hh} ! tee name=t 
            t. ! queue ! jpegdec ! videoconvert ! videoscale ! video/x-raw,format=RGBx,width={self.www},height={self.hhh} ! appsink name=raw_sink
            t. ! queue ! appsink name=jpeg_sink
        """

        self.pipeline = Gst.parse_launch(self.pipeline_description)

        self.raw_sink = self.pipeline.get_by_name("raw_sink")
        self.raw_sink.set_property("emit-signals", True)
        self.raw_sink.set_property("sync", False)
        self.raw_sink.connect("new-sample", self.on_new_buffer_raw, None)

        # Get the appsink where JPEG-encoded images will be captured
        self.jpeg_sink = self.pipeline.get_by_name("jpeg_sink")
        self.jpeg_sink.set_property("emit-signals", True)
        self.jpeg_sink.set_property("sync", False)
        self.jpeg_sink.connect("new-sample", self.on_new_buffer, None)

        # Start the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

        self.lastRaw = np.zeros((self.hh, self.ww, 4), dtype=np.uint8)
        success, encoded_image = cv2.imencode(".jpg", self.lastRaw)
        self.lastJpeg = encoded_image

        self.runThread = Thread(target=self.run, daemon=True)
        

    def run(self):
        loop = GLib.MainLoop()
        loop.run()

    # this is JPEG
    def on_new_buffer(self, sink, data):
        sample = sink.emit("pull-sample")
        if sample:
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            # Extract raw frame data from buffer
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                self.lastJpeg = map_info.data
                buffer.unmap(map_info)
                
                self.newJpegSignal.trigger(self.lastJpeg)
                logger.info("new jpeg image emmited")

        return Gst.FlowReturn.OK

    def on_new_buffer_raw(self, sink, data):
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        success, mapinfo = buf.map(Gst.MapFlags.READ)

        if success:
            img_data = np.frombuffer(mapinfo.data, dtype=np.uint8)
            img_data = img_data.reshape((self.hhh, self.www, 4))
            self.lastRaw = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            buf.unmap(mapinfo)
            
            self.newRawSignal.trigger(self.lastRaw)


        return Gst.FlowReturn.OK


if __name__ == "__main__":
    import time

    # Initialize GStreamer
    Gst.init(None)
    jdc = JpegDoubleCapture(1280, 720)
    while 1:
        time.sleep(1)