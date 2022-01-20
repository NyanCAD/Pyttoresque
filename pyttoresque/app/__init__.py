import os
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerJinjaMixin, ExtensionHandlerMixin
from jupyterlab_server import LabServerApp
from bokeh.embed import server_document
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

class BokehHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    def get(self):
        script = server_document()
        return self.write(
            self.render_template(
                "bokeh.html",
                script=script,
            )
        )


class Mosaic(LabServerApp):
    name = "mosaic"
    default_url = "/libman"
    static_dir = os.path.join(HERE, "static")
    templates_dir = os.path.join(HERE, "templates")

    def initialize_handlers(self):
        origin = f"{self.serverapp.ip}:{self.serverapp.port}"
        app = Application(ScriptHandler(filename=os.path.join(HERE, "simulate.py")))
        self.bokehserver = Server(app, allow_websocket_origin=[origin])
        self.bokehserver.start()

        self.handlers.append(("/libman", LibmanHandler))
        self.handlers.append(("/editor", MosaicHandler))
        self.handlers.append(("/simulate", BokehHandler))

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