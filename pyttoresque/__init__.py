from pyttoresque.app import Mosaic

def _jupyter_server_extension_points():
    return [
        {
            "module": "pyttoresque.app",
            "app": Mosaic
        }
    ]
