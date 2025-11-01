from nicegui import ui, events, app, Event
import threading

class UiGen:
    def __init__(self):
        self.controls = {}
        self.inc = 0

    def run(self):
        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()

    def host(self):
        ui.run(self.root, reload=False, show=False)

    def root(self):
        ui.sub_pages({
            "/": self.spawnGui
        })

    def fiveSecondRate(self):
        self.loadRadars()
        self.controls["theMap"].update()

    def loadRadars(self):
        m = self.controls["theMap"]
        for i in range(1000):
            self.inc += 1
            m.generic_layer(name='circle', args=[[50 + self.inc/1000, 20], {"radius": 300, "color": "#FFFFFF", "fill": False}])


    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()

        # with ui.header().classes("bg-gray-800 text-white justify-between p-2"):


        with ui.column().classes('w-full max-w-1280px mx-auto flex-1'):

            self.carMoveEvent = Event()

            

            self.controls["theMap"] = ui.leaflet(center=(52.198769, 19.228751),
                                                zoom=6,
                                                additional_resources=['/rotatedMarker.js']
                                                ).classes('w-full h-[calc(33vh)]')
            #self.justMaps.append(self.controls["theMap"])
            #logger.info(f"there are {len(self.justMaps)} maps in the memory")
            #self.controls["theMap"].on('map-mousemove', self.handleMouseMove)
            self.loadRadars()
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
                        
                    

                    
        ui.timer(interval=2, callback=self.fiveSecondRate)


        self.rendered = True

if __name__ == "__main__":
    import time

    ug = UiGen()
    ug.run()
    while 1:
        time.sleep(1)