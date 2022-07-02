import os

from controllers.base_controller import BaseController
from route import ApiRoute, ApiVersion, Route


class RootController(BaseController):
    def get(self, path):
        file_path = os.path.abspath(os.path.dirname(__file__)) + "/../public/"
        with open(file_path + "index.html", 'r') as file:
            self.write(file.read())


class StaticController(BaseController):
    def get(self):
        self.set_header('Content-Type', '')
        file_path = os.path.abspath(os.path.dirname(__file__)) + "/../static/"
        with open(file_path + self.request.uri, 'r') as file:
            self.write(file.read())


@Route('/debug')
class DebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK'})


@ApiRoute('debug', ApiVersion.v1)
class ApiDebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK', 'api_version': 1})
