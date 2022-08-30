# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0

import os
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.extension.handler import ExtensionHandlerJinjaMixin, ExtensionHandlerMixin
from jupyter_server.extension.application import ExtensionApp, ExtensionAppJinjaMixin
from tornado.web import addslash
from traitlets import Unicode
from configparser import ConfigParser
from secrets import token_hex
from base64 import b64encode

HERE = os.path.dirname(__file__)

class LibmanHandler(ExtensionHandlerJinjaMixin, ExtensionHandlerMixin, JupyterHandler):
    @addslash
    def get(self):
        return self.write(
            self.render_template(
                "libman.html",
                static=self.static_url,
                token=self.settings["token"],
                couchdb=self.settings['mosaic_config']['couchdb'],
                couchdb_sync=self.settings['mosaic_config']['couchdb_sync'],
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
                couchdb=self.settings['mosaic_config']['couchdb'],
                couchdb_sync=self.settings['mosaic_config']['couchdb_sync'],
            )
        )

class Mosaic(ExtensionAppJinjaMixin, ExtensionApp):
    name = "mosaic"
    default_url = "/mosaic"
    static_paths = [os.path.join(HERE, "static")]
    template_paths = [os.path.join(HERE, "templates")]

    couchdb = Unicode("proxy", help="CouchDB URL to use").tag(config=True)
    couchdb_sync = Unicode(help="Remote CouchDB URL to synch PouchDB with").tag(config=True)
    
    def initialize_settings(self):
        super().initialize_settings()

    def initialize_handlers(self):
        self.handlers.append((r"/mosaic/?", LibmanHandler))
        self.handlers.append((r"/mosaic/editor/?", MosaicHandler))

        super().initialize_handlers()


def main():
    Mosaic.launch_instance()


def setup_couchdb():
    password = os.environ.setdefault("COUCHDB_ADMIN_PASSWORD", token_hex())
    auth = "Basic " + b64encode(f"admin:{password}".encode()).decode()
    def command(port):
        os.environ["COUCHDB_LISTEN_PORT"] = str(port)
        tmpl = os.path.join(HERE, "templates", "local.ini")
        cp = ConfigParser()
        cp.read(tmpl)
        cp['admins']['admin'] = password
        cp['chttpd']['port'] = str(port)
        # we'd like to use a temporary file here
        # but couchdb writes the uuid to local.ini
        # and this affects replication
        # so we have to use a persistent file
        with open(tmpl, 'w') as f:
            cp.write(f)
        cmd = ['couchdb', '-couch_ini', tmpl]
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
                    '--address', '127.0.0.1',
                    '--port', '{port}', HERE],
        'absolute_url': True,
        'timeout': 10,
    }

if __name__ == "__main__":
    main()