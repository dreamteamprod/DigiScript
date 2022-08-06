import os
from tornado.escape import url_unescape

from controllers.base_controller import BaseController, BaseAPIController
from utils.route import ApiRoute, ApiVersion, Route

# Controller imports - used to trigger the decorator
# pylint: disable=unused-import
import controllers.api.settings
import controllers.api.show.cast
import controllers.api.show.shows
import controllers.api.websocket
# pylint: enable=unused-import


class RootController(BaseController):
    def get(self, path):
        file_path = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),
            "..",
            "public")
        with open(os.path.join(file_path, "index.html"), 'r') as file:
            self.write(file.read())


class StaticController(BaseController):
    def get(self):
        self.set_header('Content-Type', '')
        full_path = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)), "..", "static", url_unescape(
                self.request.uri).strip(
                os.path.sep))
        try:
            with open(full_path, 'r') as file:
                self.write(file.read())
        except UnicodeDecodeError:
            with open(full_path, 'rb') as file:
                self.write(file.read())


class ApiFallback(BaseAPIController):
    def get(self):
        self.set_status(404)
        self.write({'message': '404 not found'})

    def post(self):
        self.set_status(404)
        self.write({'message': '404 not found'})

    def patch(self):
        self.set_status(404)
        self.write({'message': '404 not found'})

    def delete(self):
        self.set_status(404)
        self.write({'message': '404 not found'})


@Route('/debug')
class DebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK'})


@ApiRoute('debug', ApiVersion.v1)
class ApiDebugController(BaseAPIController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK', 'api_version': 1})
