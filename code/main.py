import time
from Util import printMotd
from webgui import WebguiRoot
from data_source_elements import GpsHandler
from camera_stuff import Camera
from logging_setup import get_logger

logger = get_logger(__name__)
CAMERA_FPS = 30.0





class mainClass:
    def __init__(self):
        self.webgui = WebguiRoot(camera_fps=CAMERA_FPS)
        self.gps = GpsHandler()
        self.gps.newPositionSignal.addReceiver(self.new_gps)

        self.camera = Camera(
            #"/dev/v4l/by-id/usb-Arducam_Technology_Co.__Ltd._Arducam_1080P_Low_Light_UC684-video-index0",
            "/dev/video0",
            (1920, 1080), fps=CAMERA_FPS,
        )
        self.camera.new_jpeg_signal.addReceiver(self.handle_new_camera_jpeg)
        self.camera.start()

        self.webgui.run()

    def handle_new_camera_jpeg(self, jpeg):
        self.webgui.new_camera_jpeg_signal.trigger(jpeg)

    def new_gps(self, parser):
        self.webgui.main_screen.update_gps_status(parser.status)



def main() -> None:
    printMotd()
    mainClass()

    while(1):
        time.sleep(5)

if __name__ == '__main__':
    main()
