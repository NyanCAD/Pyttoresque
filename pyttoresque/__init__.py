from pyttoresque.app import Mosaic

def _jupyter_server_extension_points():
    return [
        {
            "module": "pyttoresque.app",
            "app": Mosaic
        }
    ]

# notebook server compat
load_jupyter_server_extension = Mosaic.load_classic_server_extension