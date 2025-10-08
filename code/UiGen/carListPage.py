from nicegui import ui
import time

class CarListPage:
    def __init__(self):
        self.controls = {}
        
        
    def updateBatteryData(self, data):
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
    
    def updateGpsData(self, data):
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


    def spawnGui(self):
        dark = ui.dark_mode()
        dark.enable()
        if(False):
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
