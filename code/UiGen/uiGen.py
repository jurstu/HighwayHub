from nicegui import ui, events, app, Event
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
from .carListPage import CarListPage
from .videoLivePage import VideoLivePage

logger = getLogger(__name__)

class UiGen:
    def __init__(self):
        self.controls = {}
        self.updatePositionMessage = Event[float, float]()
        self.lon = 21
        self.lat = 51


    def run(self):
        logger.info("setting up nicegui server")
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def ngStartedCb(self):
        pass

    def host(self):
        with redirect_stdout(StdoutInterceptor("." + __name__ + ".NiceGUI", self.ngStartedCb)):
            ui.run(self.idk, reload=False, show=False)

    def idk(self):
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

        ui.sub_pages({
            "/": self.spawnGui
        })

    
    def handleMouseMove(self, e: events.GenericEventArguments):
        lat = e.args['latlng']['lat']
        lon = e.args['latlng']['lng']
        watcherObject = self.ic.getValue("RadarWatcherObject")
        watcherObject.getDistances([lat, lon])

    def changePosition(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.updatePositionMessage.emit(lat, lon)

    
    def updatePositionData(self, marker, lat, lon):
        marker.move(lat, lon)

    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()
        self.controls["map"] = ui.leaflet(center=[52, 21], zoom=9).classes("w-200 h-200")
        self.controls["carMarker"] = self.controls["map"].marker(latlng=(self.lat, self.lon))
        from functools import partial
        self.updatePositionMessage.subscribe(partial(self.updatePositionData, self.controls["carMarker"]))
        #self.updatePositionMessage.subscribe(lambda lat, lon: self.updatePositionData(self.controls["carMarker"], lat, lon))


        @app.get("/video/frame", response_class=Response)
        def grabVideoFrame() -> Response:
            return Response(content=self.state.latestFrameJpeg, media_type="image/jpg")

        @app.get("/car.png")
        def serve_dynamic_image():
            return FileResponse("./assets/car.png", media_type='image/png')

        @app.get("/radar.png")
        def serve_dynamic_image():
            return FileResponse("./assets/radar.png", media_type='image/png')


        @app.get("/rotatedMarker.js")
        def serve_dynamic_image():
            return FileResponse("./UiGen/leaflet.rotatedMarker.js", media_type='text/javascript')

        self.rendered = True

if __name__ == "__main__":
    from .uiGen import UiGen
    import time

    ug = UiGen()
    ug.run()
    i = 0
    while 1:
        time.sleep(0.1)
        logger.info("changing position")
        lat = 52 + 0.3*np.sin((i/100)/np.pi)
        lon = 21 + 0.3*np.cos((i/100)/np.pi)
        
        ug.changePosition(lat, lon)
        i += 10