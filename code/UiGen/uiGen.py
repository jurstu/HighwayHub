from nicegui import ui, events, app
from fastapi import Response
from fastapi.responses import FileResponse
import os
import time
from Util import EmptyClass, StdoutInterceptor
from contextlib import redirect_stdout
import numpy as np
import cv2
import threading
import base64
from LoggingSetup import getLogger
from DataSource import InformationCenter
import json

logger = getLogger(__name__)


class UiGen:
    def __init__(self):
        self.ngStarted = 0
        self.state = EmptyClass()
        self.ic = InformationCenter()



        self.controls = {}
        self.spawnGui()
        self.loadSettingsFromParams(self.ic.getValue("PARAMS"))

    def run(self):
        logger.info("setting up nicegui server")
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def ngStartedCb(self):
        self.ngStarted = 1

    def host(self):
        with redirect_stdout(StdoutInterceptor("." + __name__ + ".NiceGUI", self.ngStartedCb)):
            ui.run(reload=False, show=False)

    def loadSettingsFromParams(self, params):
        self.state.hh = params["firstVideoSettings"]["hh"]
        self.state.ww = params["firstVideoSettings"]["ww"]
        self.state.latestFrameJpeg = np.zeros((self.state.hh, self.state.ww, 3), dtype=np.uint8)
        _, self.state.latestFrameJpeg = cv2.imencode(".jpg", self.state.latestFrameJpeg)
        self.state.latestFrameJpeg = self.state.latestFrameJpeg.tobytes()

    def updateAtVideoRate(self):
        pass

    def fiveSecondRate(self):
        lastGpsUpdate = self.ic.getValue("last gps update ts", 0)
        if(time.time() - lastGpsUpdate > 2):
            a = EmptyClass()
            a.fix = False
            self.updateGpsData(a)

    def updateGpsData(self, data):
        self.controls["GPS card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")

        status = data.fix
        if status == 0:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-red-500")
        else:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-green-500")
            self.controls[f"GPS card lat"].text = "{:03.5f}°".format(data.lat)
            self.controls[f"GPS card lon"].text = "{:03.5f}°".format(data.lon)
            self.controls[f"GPS card alt"].text = "{:03.5f}m".format(data.alt)

            cc = self.ic.getValue("car-centered", False)
            if(cc):
                self.controls["theMap"].set_center((data.lat, data.lon))
            
            if(not "carMarker" in self.controls):
                self.controls["carMarker"] = self.controls["theMap"].marker(latlng=(data.lat, data.lon), options={'rotationAngle': data.COG, "rotationOrigin": "center center"})
                self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')
            else:
                self.controls["carMarker"].move(data.lat, data.lon)
                self.controls["carMarker"].run_method(':setRotationAngle', "{:d}".format(data.COG))
                self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')

        self.updatePath()

    def updatePath(self):
        recentPaths = self.ic.getValue("recentPositionsList")
        positions = []
        speeds = []
        alts = []

        for data in recentPaths:
            positions.append([data.lat, data.lon])
            speeds.append([data.SOG, data.COG])
            alts.append(data.alt)

        if("trace" in self.controls):
           self.controls["theMap"].remove_layer(self.controls["trace"])
           

        self.controls["trace"] = self.controls["theMap"].generic_layer(name='polyline', args=[positions, {"color": "red"}]) 
        self.controls["elevationChart"].options['series'][0]['data'] = alts
        self.controls["elevationChart"].update()



    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()

        # with ui.header().classes("bg-gray-800 text-white justify-between p-2"):
        with ui.footer().classes("bg-gray-800 text-white p-2 items-stretch"):  # force vertical stretch
            with ui.row().classes("w-full items-stretch"):
                with ui.card().classes("h-full px-4 rounded bg-slate-500") as card:
                    self.controls["GPS card"] = card
                    with ui.column().style("gap: 0.1rem").classes("h-full") as col:
                        self.controls[f"GPS card StatusCol"] = col
                        self.controls[f"GPS card StatusLab"] = ui.label(f"{'GPS card'} STATUS")
                        self.controls[f"GPS card lat"] = ui.label("")
                        self.controls[f"GPS card lon"] = ui.label("")
                        self.controls[f"GPS card alt"] = ui.label("")


        with ui.column().classes('w-full max-w-[1280px] mx-auto flex-1'):
            self.controls["theMap"] = ui.leaflet(additional_resources=[
                '/rotatedMarker.js'
            ]).classes('w-full h-[calc(33vh)]')

            with ui.card().classes('w-full bg-gray-100 h-[calc(33vh)]'):
                self.controls["elevationChart"] = ui.echart({
                    "animation": False,
                    "legend": {"data": ["elevation [m]"]},
                    "xAxis": {"type": "category"},
                    "yAxis": {
                        "type": "value",
                        "scale": True,
                        "axisLabel": {
                            #":formatter": "function (value) { return Number.isInteger(value) ? value : ''; }"
                        },
                    },
                    "series": [
                        {"name": "elevation [m]", "color": "blue", "type": "line", "data": []}
                    ],
                }).classes("w-full h-full")
                
        
        ui.timer(interval=0.033, callback=self.updateAtVideoRate)
        ui.timer(interval=2, callback=self.fiveSecondRate)

        @app.get("/video/frame", response_class=Response)
        def grabVideoFrame() -> Response:
            return Response(content=self.state.latestFrameJpeg, media_type="image/jpg")

        @app.get("/car.png")
        def serve_dynamic_image():
            return FileResponse("./assets/car.png", media_type='image/png')

        @app.get("/rotatedMarker.js")
        def serve_dynamic_image():
            return FileResponse("./UiGen/leaflet.rotatedMarker.js", media_type='text/javascript')

if __name__ == "__main__":
    from .uiGen import UiGen
    import time

    ug = UiGen()
    ug.run()
    while 1:
        time.sleep(1)