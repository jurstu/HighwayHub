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
from functools import partial

logger = getLogger(__name__)


class UiGen:
    def __init__(self):
        self.controls = {}
        self.updatePositionMessage = Event()
        self.updateBatteryMessage = Event()
        self.updateElevationMessage = Event()
        
        self.state = EmptyClass()
        self.state.lon = 0
        self.state.lat = 0
        self.state.follow = False

        self.ic = InformationCenter()
        #self.loadSettingsFromParams(self.ic.getValue("PARAMS"))


    def run(self):
        logger.info("setting up nicegui server")
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def ngStartedCb(self):
        pass

    def host(self):
        with redirect_stdout(StdoutInterceptor("." + __name__ + ".NiceGUI", self.ngStartedCb)):
            ui.run(self.root, reload=False, show=False)

    def root(self):
        with ui.footer().classes("bg-gray-800 text-white p-2 items-stretch"):  # force vertical stretch
            with ui.row().classes("w-full items-stretch"):
                with ui.card().classes("h-full px-4 rounded bg-slate-500") as card:
                    self.controls["GPS card"] = card
                    with ui.column().style("gap: 0.1rem").classes("h-full items-center justify-center") as col:
                        self.controls["GPS card StatusCol"] = col
                        self.controls["GPS card StatusLab"] = ui.label("GPS STATUS")
                        self.controls["GPS card lat"] = ui.label(" ")
                        self.controls["GPS card lon"] = ui.label(" ")
                        self.controls["GPS card alt"] = ui.label(" ")
                        self.controls["followSwitch"] = ui.switch('follow', on_change=self.followSwitchChanged, value=self.state.follow)

                with ui.card().classes("h-full px-4 rounded bg-slate-500 flex items-center justify-center") as card:
                    self.controls["BATT card"] = card
                    with ui.column().style("gap: 0.1rem").classes("h-full items-center justify-center"):
                        self.controls["BATT card StatusLab"] = ui.label("BATTERY STATUS")
                        self.controls["BATT card percent"] = ui.label(" ")
                        self.controls["BATT card status"] = ui.label(" ")
                        self.controls["BATT card noneLabel"] = ui.label(" ")

                

        self.updatePositionMessage.subscribe(partial(self.updateGpsCard, self.controls.copy()))
        self.updateBatteryMessage.subscribe(partial(self.updateBatteryCard, self.controls.copy()))

        ui.sub_pages({
            "/": self.spawnGui
        })

    def updateElevationData(self, data):
        self.updateElevationMessage.emit(data)
        
    def updateElevationCard(self, controls, data):
        controls["elevationChart"].options['series'][0]['data'] = data
        controls["elevationChart"].update()

    def updateGpsData(self, data):
        self.updatePositionMessage.emit(data)

    def updateGpsCard(self, controls, data):
        controls["followSwitch"].value = self.state.follow

        if data is None:
            return
        controls["GPS card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")
        status = data.fix
        if status == 0:
            controls["GPS card"].classes("px-4 py-1 rounded bg-red-500")
        else:
            controls["GPS card"].classes("px-4 py-1 rounded bg-green-500")
            controls[f"GPS card lat"].text = "{: 3.5f}°".format(data.lat)
            controls[f"GPS card lon"].text = "{: 3.5f}°".format(data.lon)
            controls[f"GPS card alt"].text = "{: 3.1f}m".format(data.alt)

            
    def followSwitchChanged(self, e):
        logger.info(f"follow switch switched to {e.value}")
        self.state.follow = e.value
        self.updatePositionMessage.emit(None)





    def updateBatteryData(self, data):
        self.updateBatteryMessage.emit(data)

    def updateBatteryCard(self, controls, data):
        controls["BATT card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")
        controls[f"BATT card percent"].text = "{: 2d}%".format(data.battPercent)
        controls[f"BATT card status"].text = "{}".format(data.chargingStatus)
        if(data.battCurrent < 0):
            controls["BATT card noneLabel"].text = f"time to full {data.timeToFull}"
        else:
            controls["BATT card noneLabel"].text = f"time to empty {data.timeToEmpty}"
        perc = data.battPercent
        if(data.allGood):
            if(perc > 50):
                controls["BATT card"].classes("px-4 py-1 rounded bg-green-500")
            elif(perc > 20):
                controls["BATT card"].classes("px-4 py-1 rounded bg-yellow-500")
            else:
                controls["BATT card"].classes("px-4 py-1 rounded bg-red-500")
        else:
            controls["BATT card"].classes("px-4 py-1 rounded bg-red-500")
            controls[f"BATT card percent"].text = ""
            controls[f"BATT card status"].text = "no data from controller"
            controls["BATT card noneLabel"].text = f" "

        
    def modifyCarMarker(self, controls, data):
        if data is None:
            return
        marker = controls["carMarker"]
        m = controls["map"]
        lat = data.lat
        lon = data.lon
        angle = data.COG
        marker.move(lat, lon)
        marker.run_method(':setRotationAngle', "{:d}".format(angle))
        marker.run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')
        cc = self.state.follow
        if(cc):
            m.set_center((data.lat, data.lon))



    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()
        with ui.column().classes("w-full gap-2").style("width: 100vw; max-width: 100%;"):
            self.controls["map"] = ui.leaflet(center=[52, 21], zoom=9, additional_resources=['/rotatedMarker.js']).classes("w-full").style("width: 100%; height: 60vh; min-height: 320px; max-height: 700px;")
            #elf.updatePositionMessage.subscribe(lambda lat, lon: self.updatePositionData(self.controls["carMarker"], lat, lon))

            with ui.card().classes('w-full bg-gray-100').style("min-height: 260px; width: 100%;"):
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
                }).classes("w-full").style("width: 100%; height: 260px;")

        self.updateElevationMessage.subscribe(partial(self.updateElevationCard, self.controls.copy()))

        @app.get("/car.png")
        def serve_dynamic_image():
            return FileResponse("./assets/car.png", media_type='image/png')

        @app.get("/radar.png")
        def serve_dynamic_image():
            return FileResponse("./assets/radar.png", media_type='image/png')


        @app.get("/rotatedMarker.js")
        def serve_dynamic_image():
            return FileResponse("./UiGen/leaflet.rotatedMarker.js", media_type='text/javascript')

        self.loadRadars()
        self.controls["carMarker"] = self.controls["map"].marker(latlng=(self.state.lat, self.state.lon), options={'rotationAngle': 0, "rotationOrigin": "center center"})

        self.updatePositionMessage.subscribe(partial(self.modifyCarMarker, self.controls.copy()))

        self.controls["carMarker"].run_method(':setRotationAngle', "{:d}".format(0))
        self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')





    def loadRadars(self):
        try:
            with open("assets/canard_detailed_data.json", "r") as f:
                data = json.load(f)
            
        except Exception as e:
            logger.warning(f"couldn't load canard data {e}")
            data = {}

        wo = self.ic.getValue("RadarWatcherObject")
        if(wo is not None):
            detectionRadius = wo.detectionEntryRadius
        else:
            detectionRadius = 500

        m = self.controls["map"]
        for k, recData in data.items():            
            # we actually don't need the key, but wth
            lat = recData["lat"]
            lon = recData["lon"]
            if("urzadzenie" in recData):
                devType = recData["urzadzenie"]["rodzajPomiaru"]
                color = "#FFFFFF"
                if(devType == "PO"):
                    color = "#0000C0"
                    endpointLoc = recData["urzadzenie"]["lokalizacjaDrugiegoPunktu"].split(";")
                    lon2, lat2 = [float(x) for x in endpointLoc]
                    #logger.debug(f"{lat2} {lon2}")
                    m.generic_layer(name='circle', args=[[lat2, lon2], {"radius": detectionRadius+10, "color": color, "fill": False}])
                    m.generic_layer(name='polyline', args=[[[lat, lon],[lat2, lon2]], {"color": "purple"}]) 
                elif(devType == "PC"):
                    color = "#c00000"
                elif(devType == "PP"):
                    color = "#c0c000"
                m.generic_layer(name='circle', args=[[lat, lon], {"radius": detectionRadius, "color": color, "fill": False}])
                m.generic_layer(name='circle', args=[[lat, lon], {"radius": 10, "color": color, "fill": True}])
                #radarMarker = m.marker(latlng=(lat, lon), options={'rotationAngle': 0, "rotationOrigin": "center center"})
                # the icons don't change properly here
                #radarMarker.run_method(':setIcon', 'L.icon({iconUrl: "/radar.png", iconSize: [32, 32], iconAnchor: [16, 16]})')

                #controlsKey = f"radar_{k}"


if __name__ == "__main__":
    from .uiGen import UiGen
    import time

    ug = UiGen()
    ug.run()
    i = 0
    while 1:
        time.sleep(0.1)
        logger.info("changing position")
        lat = 52 + 0.3*np.sin((i/100)*np.pi)
        lon = 21 + 0.3*np.cos((i/100)*np.pi)
        
        ug.changePosition(lat, lon, int(-i*180/100))
        i += 1
