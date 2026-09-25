from nicegui import ui, app
from .main_screen import MainScreen

import threading

class WebguiRoot:
    def __init__(
        self,
        port=8080
    ):
        self.main_screen = MainScreen()
        self.port = port
        self.running = False

    def run(self):
        if self.running:
            return

        self.t = threading.Thread(target=self.host, daemon=True)
        self.t.start()
        self.running = True

    def host(self):
        ui.run(self.root, reload=False, show=False, port=self.port)

    def root(self):
        ui.sub_pages({
                        '/': self.spawn_gui,
                        "/main_navigation_screen": self.main_screen.spawn_gui,
                      })

    def spawn_gui(self):
        @ui.page("/")
        def index():
            dark = ui.dark_mode()
            dark.enable()
            ui.link('main nav', '/main_navigation_screen')