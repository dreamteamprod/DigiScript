import os

from tornado.escape import url_unescape
from tornado.web import HTTPError
from tornado_prometheus import MetricsHandler

from digi_server.logger import get_logger
from utils.module_discovery import get_resource_path, import_modules, is_frozen
from utils.web.base_controller import BaseAPIController, BaseController
from utils.web.route import ApiRoute, ApiVersion, Route

IMPORTED_CONTROLLERS = {}


def import_all_controllers():
    get_logger().info("Importing controllers...")
    import_modules("controllers", IMPORTED_CONTROLLERS, __name__)

    # Log summary
    get_logger().info(f"Imported {len(IMPORTED_CONTROLLERS)} controller modules")
    get_logger().debug(f"Imported controllers: {list(IMPORTED_CONTROLLERS.keys())}")


class RootController(BaseController):
    def get(self, _path):
        if is_frozen():
            # In PyInstaller mode, use resource path
            full_path = get_resource_path(os.path.join("static", "index.html"))
        else:
            # In source mode, use relative path
            file_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "..", "static"
            )
            full_path = os.path.join(file_path, "index.html")

        if not os.path.isfile(full_path):
            get_logger().error(f"Index file not found: {full_path}")
            raise HTTPError(404)

        try:
            with open(full_path, "r", encoding="utf-8") as file:
                self.write(file.read())
        except Exception as e:
            get_logger().error(f"Error serving index.html: {str(e)}")
            raise HTTPError(500) from e


class StaticController(BaseController):
    def get(self):
        self.set_header("Content-Type", "")

        uri = url_unescape(self.request.uri).strip(os.path.sep)

        if is_frozen():
            # In PyInstaller mode, use resource path
            full_path = get_resource_path(uri)
        else:
            # In source mode, use relative path
            full_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "..",
                "static",
                url_unescape(self.request.uri).strip(os.path.sep),
            )

        if not os.path.isfile(full_path):
            get_logger().warning(f"Static file not found: {full_path}")
            raise HTTPError(404)

        try:
            with open(full_path, "r", encoding="utf-8") as file:
                self.write(file.read())
        except UnicodeDecodeError:
            try:
                with open(full_path, "rb") as file:
                    self.write(file.read())
            except Exception as exc:
                get_logger().error(f"Error reading binary file {full_path}: {str(exc)}")
                raise HTTPError(500) from exc
        except Exception as exc:
            get_logger().error(f"Error reading file {full_path}: {str(exc)}")
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
