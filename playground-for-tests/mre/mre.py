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

    def refresh(self):
        self.loadRadars()
        self.controls["theMap"].update()

    def loadRadars(self):
        m = self.controls["theMap"]
        for i in range(1000):
            self.inc += 1
            m.generic_layer(name='circle', args=[[50 + self.inc/1000, 20], {"radius": 300, "color": "#FF00FF", "fill": False}])

    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()
        
        self.controls["theMap"] = ui.leaflet(center=(52.198769, 19.228751),
                                            zoom=6,
                                            ).classes('w-320 h-320')

        self.loadRadars()                    
        ui.timer(interval=1, callback=self.refresh)
        self.rendered = True

if __name__ == "__main__":
    import time

    ug = UiGen()
    ug.run()

    while(1):
        time.sleep(1)

