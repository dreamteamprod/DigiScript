import os

from tornado.web import HTTPError

from digi_server.logger import get_logger
from utils.module_discovery import get_resource_path, is_frozen
from utils.web.base_controller import BaseController
from utils.web.route import Route


@Route("/v3")
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
