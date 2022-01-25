import os
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerJinjaMixin, ExtensionHandlerMixin
from jupyter_server.extension.application import ExtensionApp, ExtensionAppJinjaMixin
from bokeh.server.server import Server
from bokeh.application.handlers import ScriptHandler
from bokeh.application import Application

HERE = os.path.dirname(__file__)


class LibmanHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    def get(self):
        return self.write(
            self.render_template(
                "libman.html",
                static=self.static_url,
                token=self.settings["token"],
            )
        )

class MosaicHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    def get(self):
        return self.write(
            self.render_template(
                "editor.html",
                static=self.static_url,
                token=self.settings["token"],
            )
        )

class Mosaic(ExtensionAppJinjaMixin, ExtensionApp):
    name = "mosaic"
    default_url = "/libman"
    static_paths = [os.path.join(HERE, "static")]
    template_paths = [os.path.join(HERE, "templates")]

    def initialize_handlers(self):
        bokehapps = {
            "/simulate": Application(ScriptHandler(filename=os.path.join(HERE, "simulate.py")))
        }
        self.bokehserver = Server(bokehapps, io_loop=self.serverapp.io_loop, allow_websocket_origin=["*"])
        self.bokehserver.start()

        self.handlers.append(("/libman", LibmanHandler))
        self.handlers.append(("/editor", MosaicHandler))

        super().initialize_handlers()

    async def stop_extension(self):
        try:
            self.bokehserver.stop()
        except Exception:
            pass
        await super().stop_extension()


def main():
    Mosaic.launch_instance()

if __name__ == "__main__":
    main()