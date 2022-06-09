# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0

import os
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerJinjaMixin, ExtensionHandlerMixin
from jupyter_server.extension.application import ExtensionApp, ExtensionAppJinjaMixin
from tornado.web import addslash
from traitlets import Bool
from shutil import which
from tempfile import NamedTemporaryFile
from configparser import ConfigParser
from secrets import token_hex
from base64 import b64encode

HERE = os.path.dirname(__file__)

has_couchdb = bool(which("couchdb"))

class LibmanHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    @addslash
    def get(self):
        return self.write(
            self.render_template(
                "libman.html",
                static=self.static_url,
                token=self.settings["token"],
                couchdb=has_couchdb,
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
                couchdb=has_couchdb,
            )
        )

class Mosaic(ExtensionAppJinjaMixin, ExtensionApp):
    name = "mosaic"
    default_url = "/mosaic"
    static_paths = [os.path.join(HERE, "static")]
    template_paths = [os.path.join(HERE, "templates")]
    
    def initialize_settings(self):
        super().initialize_settings()

    def initialize_handlers(self):
        self.handlers.append((r"/mosaic/?", LibmanHandler))
        self.handlers.append((r"/mosaic/editor/?", MosaicHandler))

        super().initialize_handlers()


def main():
    Mosaic.launch_instance()


def setup_couchdb():
    password = os.environ.get("COUCHDB_ADMIN_PASSWORD", token_hex())
    auth = "Basic " + b64encode(f"admin:{password}".encode()).decode()
    def command(port):
        tmpl = os.path.join(HERE, "templates", "local.ini")
        cp = ConfigParser()
        cp.read(tmpl)
        cp['admins']['admin'] = password
        cp['chttpd']['port'] = str(port)
        tf = NamedTemporaryFile('w', suffix='local.ini', delete=False)
        cp.write(tf)
        cmd = ['couchdb', '-couch_ini', tf.name]
        if os.name == 'nt':
            cmd = ["cmd.exe", "/c"] + cmd
        return cmd
    return {
        'command': command,
        'request_headers_override': {"Authorization": auth},
        'timeout': 10,
    }

def setup_panel():
    return {
        'command': ['panel', 'serve',
                    '--allow-websocket-origin', '*',
                    '--prefix', '{base_url}/panel',
                    '--port', '{port}', HERE],
        'absolute_url': True,
        'timeout': 10,
    }

if __name__ == "__main__":
    main()