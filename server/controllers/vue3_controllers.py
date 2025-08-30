import os

from tornado.escape import url_unescape
from tornado.web import HTTPError

from digi_server.logger import get_logger
from utils.module_discovery import get_resource_path, is_frozen
from utils.web.base_controller import BaseController
from utils.web.route import Route


@Route("/v3")
@Route("/v3/(.*)")
class Vue3RootController(BaseController):
    """Controller to serve the Vue 3 application at /v3/ routes."""

    def get(self, _path=""):
        if is_frozen():
            # In PyInstaller mode, use resource path
            full_path = get_resource_path(os.path.join("static-vue3", "index.html"))
        else:
            # In source mode, use relative path
            file_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "..", "static-vue3"
            )
            full_path = os.path.join(file_path, "index.html")

        if not os.path.isfile(full_path):
            get_logger().error(f"Vue 3 index file not found: {full_path}")
            raise HTTPError(
                404, "Vue 3 application not built. Run 'npm run build' in client-vue3/"
            )

        try:
            with open(full_path, "r", encoding="utf-8") as file:
                self.write(file.read())
        except Exception as e:
            get_logger().error(f"Error serving Vue 3 index.html: {str(e)}")
            raise HTTPError(500) from e


class Vue3StaticController(BaseController):
    """Controller to serve Vue 3 static assets."""

    def get(self):
        self.set_header("Content-Type", "")

        uri = url_unescape(self.request.uri).strip(os.path.sep)
        # Remove /v3/ prefix from the URI for file lookup
        uri_parts = uri.split("/")
        if len(uri_parts) >= 3 and uri_parts[1] == "v3":
            # Reconstruct path without /v3/ prefix
            uri = "/".join(uri_parts[2:])

        if is_frozen():
            # In PyInstaller mode, use resource path
            full_path = get_resource_path(os.path.join("static-vue3", uri))
        else:
            # In source mode, use relative path
            full_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "..",
                "static-vue3",
                uri,
            )

        if not os.path.isfile(full_path):
            get_logger().warning(f"Vue 3 static file not found: {full_path}")
            raise HTTPError(404)

        try:
            # Determine content type based on file extension
            if full_path.endswith(".js"):
                self.set_header("Content-Type", "application/javascript")
            elif full_path.endswith(".css"):
                self.set_header("Content-Type", "text/css")
            elif full_path.endswith(".json"):
                self.set_header("Content-Type", "application/json")
            elif full_path.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico")):
                # Handle binary files
                with open(full_path, "rb") as file:
                    self.write(file.read())
                return

            # Handle text files
            with open(full_path, "r", encoding="utf-8") as file:
                self.write(file.read())
        except UnicodeDecodeError:
            try:
                with open(full_path, "rb") as file:
                    self.write(file.read())
            except Exception as exc:
                get_logger().error(
                    f"Error reading Vue 3 binary file {full_path}: {str(exc)}"
                )
                raise HTTPError(500) from exc
        except Exception as exc:
            get_logger().error(f"Error reading Vue 3 file {full_path}: {str(exc)}")
            raise HTTPError(500) from exc
