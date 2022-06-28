from tornado.web import Application, StaticFileHandler

from route import Route
import controllers


class DigiScriptServer(Application):

    def __init__(self, debug=False):
        handlers = Route.routes()
        handlers.append((
            r'/(.*)',
            StaticFileHandler,
            {'path': 'static', 'default_filename': 'index.html'},
        ))
        super().__init__(handlers=handlers, debug=debug)
