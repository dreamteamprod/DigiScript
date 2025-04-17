import importlib
import os

from tornado.escape import url_unescape
from tornado.web import HTTPError
from tornado_prometheus import MetricsHandler

from digi_server.logger import get_logger
from utils.pkg_utils import find_end_modules
from utils.web.base_controller import BaseAPIController, BaseController
from utils.web.route import ApiRoute, ApiVersion, Route

IMPORTED_CONTROLLERS = {}


def import_all_controllers():
    controllers = find_end_modules(".", prefix="controllers")
    for controller in controllers:
        if controller != __name__:
            get_logger().debug(f"Importing controller module {controller}")
            mod = importlib.import_module(controller)
            IMPORTED_CONTROLLERS[controller] = mod


class RootController(BaseController):
    def get(self, path):
        file_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "..", "static"
        )
        full_path = os.path.join(file_path, "index.html")
        if not os.path.isfile(full_path):
            raise HTTPError(404)

        with open(full_path, "r", encoding="utf-8") as file:
            self.write(file.read())


class StaticController(BaseController):
    def get(self):
        self.set_header("Content-Type", "")
        full_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "..",
            "static",
            url_unescape(self.request.uri).strip(os.path.sep),
        )
        if not os.path.isfile(full_path):
            raise HTTPError(404)

        try:
            with open(full_path, "r", encoding="utf-8") as file:
                self.write(file.read())
        except UnicodeDecodeError:
            with open(full_path, "rb") as file:
                self.write(file.read())
        except Exception as exc:
            raise HTTPError(500) from exc


class ApiFallback(BaseAPIController):
    def get(self):
        self.set_status(404)
        self.write({"message": "404 not found"})

    def post(self):
        self.set_status(404)
        self.write({"message": "404 not found"})

    def patch(self):
        self.set_status(404)
        self.write({"message": "404 not found"})

    def delete(self):
        self.set_status(404)
        self.write({"message": "404 not found"})


@Route("/debug")
class DebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header("Content-Type", "application/json")
        self.write({"status": "OK", "imported_controllers": list(IMPORTED_CONTROLLERS)})


@ApiRoute("debug", ApiVersion.V1)
class ApiDebugController(BaseAPIController):
    def get(self):
        self.set_status(200)
        self.set_header("Content-Type", "application/json")
        self.write({"status": "OK", "api_version": 1})


@Route("/debug/metrics", ignore_logging=True)
class DebugMetricsController(MetricsHandler, BaseController):
    pass
