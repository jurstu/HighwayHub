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
from .carListPage import CarListPage
from .videoLivePage import VideoLivePage

logger = getLogger(__name__)


class UiGen:
    def __init__(self):
        self.ngStarted = 0
        self.rendered = 0
        self.state = EmptyClass()
        self.ic = InformationCenter()

        self.controls = {}
        self.carListPage = CarListPage()
        self.videoPage = VideoLivePage()
        self.radarsLoaded = 0


        self.loadSettingsFromParams(self.ic.getValue("PARAMS"))

    def run(self):
        logger.info("setting up nicegui server")
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def ngStartedCb(self):
        self.ngStarted = 1

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
            "/": self.spawnGui, 
            "/video-live": self.videoPage.spawnGui,
            "/car-list": self.carListPage.spawnGui
        })

    def loadSettingsFromParams(self, params):
        self.state.hh = params["firstVideoSettings"]["hh"]
        self.state.ww = params["firstVideoSettings"]["ww"]
        self.state.latestFrameJpeg = np.zeros((self.state.hh, self.state.ww, 3), dtype=np.uint8)
        _, self.state.latestFrameJpeg = cv2.imencode(".jpg", self.state.latestFrameJpeg)
        self.state.latestFrameJpeg = self.state.latestFrameJpeg.tobytes()

    def updateAtVideoRate(self):
        pass

    def fiveSecondRate(self):
        if(self.rendered == 0):
            return
        
        self.loadRadars()
        for k, v in self.controls.items():
            if k.startswith("radar_"):
                #logger.info(f"changing {k}")
                pass
                
        self.controls["theMap"].update()

        lastGpsUpdate = self.ic.getValue("last gps update ts", 0)
        if(time.time() - lastGpsUpdate > 2):
            a = EmptyClass()
            a.fix = False
            self.updateGpsData(a)


    def updateBatteryData(self, data):
        if(self.rendered == 0):
            return
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
        
        self.carListPage.updateBatteryData(data)
        self.videoPage.updateBatteryData(data)

    def updateGpsData(self, data):
        if(self.rendered == 0):
            return
        self.controls["GPS card"].classes(remove="bg-green-500 bg-yellow-500 bg-red-500 bg-slate-500")

        status = data.fix
        if status == 0:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-red-500")
        else:
            self.controls["GPS card"].classes("px-4 py-1 rounded bg-green-500")
            self.controls[f"GPS card lat"].text = "{: 3.5f}°".format(data.lat)
            self.controls[f"GPS card lon"].text = "{: 3.5f}°".format(data.lon)
            self.controls[f"GPS card alt"].text = "{: 3.1f}m".format(data.alt)

            cc = self.ic.getValue("car-centered", False)
            if(cc):
                self.controls["theMap"].set_center((data.lat, data.lon))
            
            try:
                if(not "carMarker" in self.controls):
                    self.controls["carMarker"] = self.controls["theMap"].marker(latlng=(data.lat, data.lon), options={'rotationAngle': data.COG, "rotationOrigin": "center center"})
                    self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')
                else:
                    self.controls["carMarker"].move(data.lat, data.lon)
                    self.controls["carMarker"].run_method(':setRotationAngle', "{:d}".format(data.COG))
                    self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')
            except Exception as e:
                logger.warning(f"problem at the car - marker {e}")
                self.controls["carMarker"] = self.controls["theMap"].marker(latlng=(data.lat, data.lon), options={'rotationAngle': data.COG, "rotationOrigin": "center center"})
                self.controls["carMarker"].run_method(':setIcon', 'L.icon({iconUrl: "/car.png", iconSize: [32, 32], iconAnchor: [16, 16]})')

        self.updatePath()
        self.carListPage.updateGpsData(data)
        self.videoPage.updateGpsData(data)

    def updatePath(self):
        if(self.rendered == 0):
            return
        recentPaths = self.ic.getValue("recentPositionsList")
        positions = []
        speeds = []
        alts = []

        for data in recentPaths:
            positions.append([data.lat, data.lon])
            speeds.append([data.SOG, data.COG])
            alts.append(data.alt)

        #if("trace" in self.controls):
        #    try:
        #        self.controls["theMap"].remove_layer(self.controls["trace"])           
        #    except Exception as e:
        #        logger.warning(f"problem with removing the last trace {e}")


        #self.controls["trace"] = self.controls["theMap"].generic_layer(name='polyline', args=[positions, {"color": "red"}]) 
        self.controls["elevationChart"].options['series'][0]['data'] = alts
        self.controls["elevationChart"].update()


    def loadRadars(self):
        if(self.radarsLoaded):
            return
        
        try:
            with open("assets/canard_detailed_data.json", "r") as f:
                data = json.load(f)
            
        except Exception as e:
            logger.warning(f"couldn't load canard data {e}")
            data = {}


        detectionRadius = self.ic.getValue("RadarWatcherObject").detectionEntryRadius
        m = self.controls["theMap"]
        for k, recData in data.items():            
            # we actually don't need the key, but wth
            lat = recData["lat"]
            lon = recData["lon"]
            if("urzadzenie" in recData):
                devType = recData["urzadzenie"]["rodzajPomiaru"]
                controlsKey = f"radar_{k}"

                color = "#FFFFFF"
                if(devType == "PO"):
                    color = "#0000C0"
                    endpointLoc = recData["urzadzenie"]["lokalizacjaDrugiegoPunktu"].split(";")
                    lon2, lat2 = [float(x) for x in endpointLoc]
                    #logger.debug(f"{lat2} {lon2}")
                    self.controls[f"{controlsKey}_endpoint"] = m.generic_layer(name='circle', args=[[lat2, lon2], {"radius": detectionRadius+10, "color": color, "fill": False}])
                    self.controls[f"{controlsKey}_line"] = self.controls["theMap"].generic_layer(name='polyline', args=[[[lat, lon],[lat2, lon2]], {"color": "purple"}]) 
                elif(devType == "PC"):
                    color = "#c00000"
                elif(devType == "PP"):
                    color = "#c0c000"

                self.controls[controlsKey] = m.generic_layer(name='circle', args=[[lat, lon], {"radius": detectionRadius, "color": color, "fill": False}])

                

                icon = 'L.icon({iconUrl: "https://leafletjs.com/examples/custom-icons/leaf-green.png"})'

                #marker = self.controls["theMap"].marker(latlng=(lat, lon))
                #marker.run_method(':setIcon', icon)
                #marker.move(51.51, -0.09)
                
                

                #self.controls[controlsKey] = marker
                

            # "punkty kontrolne " don't have no "urzadzenie" key.
            #else:
            #    logger.debug(recData.keys())


        self.radarsLoaded = 1


    def handleMouseMove(self, e: events.GenericEventArguments):
        lat = e.args['latlng']['lat']
        lon = e.args['latlng']['lng']
        watcherObject = self.ic.getValue("RadarWatcherObject")
        watcherObject.getDistances([lat, lon])

    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()

        # with ui.header().classes("bg-gray-800 text-white justify-between p-2"):


        with ui.column().classes('w-full max-w-1280px mx-auto flex-1'):
            self.controls["theMap"] = ui.leaflet(center=(52.198769, 19.228751),
                                                zoom=6,
                                                additional_resources=['/rotatedMarker.js']
                                                ).classes('w-full h-[calc(33vh)]')
            self.controls["theMap"].on('map-mousemove', self.handleMouseMove)

            #while(1):
            #    if(self.controls["theMap"].initialized()):
            #        break
            

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
            
            with ui.card().classes('w-full bg-gray-100 justify-between'):
                with ui.row().classes("w-full gap-3"):
                    with ui.button().props("flat").classes("flex-1 bg-red-600 text-white hover:bg-red-700") as cameraFeedButton:
                        ui.icon("camera").classes("text-white")
                        ui.link('  go to camera', '/video-live')
                        


                    with ui.button().props("flat").classes("flex-1 bg-green-600 text-white hover:bg-green-700") as plateListButton:
                        ui.icon("fingerprint").classes("text-white")
                        ui.link('  go to seen cars', '/car-list')
                        
                    

                    
        ui.timer(interval=0.033, callback=self.updateAtVideoRate)
        ui.timer(interval=2, callback=self.fiveSecondRate)


        

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
    while 1:
        time.sleep(1)