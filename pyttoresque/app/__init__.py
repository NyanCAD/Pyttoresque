import os
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerJinjaMixin, ExtensionHandlerMixin
from jupyter_server.extension.application import ExtensionApp, ExtensionAppJinjaMixin
from tornado.web import addslash
from traitlets import Bool

HERE = os.path.dirname(__file__)


class LibmanHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    @addslash
    def get(self):
        return self.write(
            self.render_template(
                "libman.html",
                static=self.static_url,
                token=self.settings["token"],
                couchdb=self.settings["mosaic_couchdb"],
            )
        )

class MosaicHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    @addslash
    def get(self):
        return self.write(
            self.render_template(
                "editor.html",
                static=self.static_url,
                token=self.settings["token"],
                couchdb=self.settings["mosaic_couchdb"],
            )
        )

class Mosaic(ExtensionAppJinjaMixin, ExtensionApp):
    name = "mosaic"
    default_url = "/mosaic"
    static_paths = [os.path.join(HERE, "static")]
    template_paths = [os.path.join(HERE, "templates")]
    
    couchdb = Bool(help="Use localhost CouchDB instead of PouchDB").tag(config=True)

    def initialize_settings(self):
        self.settings["mosaic_couchdb"] = self.couchdb
        super().initialize_settings()

    def initialize_handlers(self):
        self.handlers.append((r"/mosaic/?", LibmanHandler))
        self.handlers.append((r"/mosaic/editor/?", MosaicHandler))

        super().initialize_handlers()


def main():
    Mosaic.launch_instance()


def setup_pouchdb():
    return {
        # hardcode port for backend access
        'command': ['pouchdb-server', '-p', '{port}'],
        'port': 5984
    }

def setup_panel():
    return {
        'command': ['panel', 'serve',
                    '--allow-websocket-origin', '*',
                    '--prefix', '{base_url}/panel',
                    '--port', '{port}', HERE],
        'absolute_url': True,
    }

if __name__ == "__main__":
    main()