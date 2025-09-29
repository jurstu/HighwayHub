from nicegui import ui, app
from fastapi import Response
import numpy as np
import time
from DataSource import InformationCenter
import cv2

class VideoLivePage:
    def __init__(self):
        self.controls = {}
        
        self.ic = InformationCenter()
        self.params = self.ic.getValue("PARAMS")
        self.videoParams = self.params["firstVideoSettings"]
        self.ww = self.videoParams["ww"]
        self.hh = self.videoParams["hh"]
        self.latestFrameJpeg = np.zeros((self.hh, self.ww, 3), dtype=np.uint8) + 128
        _, self.latestFrameJpeg = cv2.imencode(".jpg", self.latestFrameJpeg)
        self.latestFrameJpeg = self.latestFrameJpeg.tobytes()

        ui.page(f'/video-live')(self.spawnGui)()
        
    def newJpegImage(self, image):
        #pass
        self.latestFrameJpeg = image

    def updateBatteryData(self, data):
        self.controls["BATT card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")
        self.controls[f"BATT card percent"].text = "{: 2d}%".format(data.battPercent)
        self.controls[f"BATT card status"].text = "{}".format(data.chargingStatus)
        perc = data.battPercent
        if(perc > 50):
            self.controls["BATT card"].classes("px-4 py-1 rounded bg-green-500")
        elif(perc > 20):
            self.controls["BATT card"].classes("px-4 py-1 rounded bg-yellow-500")
        else:
            self.controls["BATT card"].classes("px-4 py-1 rounded bg-red-500")
    
    def updateGpsData(self, data):
        self.controls["GPS card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")

        status = data.fix
        if status == 0:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-red-500")
        else:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-green-500")
            self.controls[f"GPS card lat"].text = "{: 3.5f}°".format(data.lat)
            self.controls[f"GPS card lon"].text = "{: 3.5f}°".format(data.lon)
            self.controls[f"GPS card alt"].text = "{: 3.1f}m".format(data.alt)


    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()


        with ui.column().classes('w-full max-w-[1280px] mx-auto flex-1'):
            with ui.card().classes('w-full bg-gray-100 aspect-video'):
                self.controls["video-image"] = (
                    ui.interactive_image("/video/frame5")
                    .classes("w-full h-full object-contain")
                )


        with ui.footer().classes("bg-gray-800 text-white p-2 items-stretch"):  # force vertical stretch
            with ui.row().classes("w-full items-stretch"):
                with ui.card().classes("h-full px-4 rounded bg-slate-500") as card:
                    self.controls["GPS card"] = card
                    with ui.column().style("gap: 0.1rem").classes("h-full items-center justify-center") as col:
                        self.controls["GPS card StatusCol"] = col
                        self.controls["GPS card StatusLab"] = ui.label("GPS STATUS")
                        self.controls["GPS card lat"] = ui.label("")
                        self.controls["GPS card lon"] = ui.label("")
                        self.controls["GPS card alt"] = ui.label("")
                with ui.card().classes("h-full px-4 rounded bg-slate-500 flex items-center justify-center") as card:
                    self.controls["BATT card"] = card
                    with ui.column().style("gap: 0.1rem").classes("h-full items-center justify-center") as col:
                        self.controls["BATT card StatusCol"] = col
                        self.controls["BATT card StatusLab"] = ui.label("BATTERY STATUS")
                        self.controls["BATT card percent"] = ui.label("")
                        self.controls["BATT card status"] = ui.label("")
                        self.controls["BATT card noneLabel"] = ui.label("")

        ui.timer(interval=0.033, callback=lambda: self.controls["video-image"].set_source(f"/video/frame5?{time.time()}"))

        @app.get("/video/frame5", response_class=Response)
        def grabVideoFrame() -> Response:
            #import base64
            black_1px = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII='
            #return Response(content="asdf".encode(), media_type='', headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
            #return Response(content=base64.b64decode(black_1px.encode('ascii')), media_type='image/png')
            return Response(content=self.latestFrameJpeg, media_type="image/jpg", headers={"Cache-Control": "no-store, no-cache, must-revalidate"})