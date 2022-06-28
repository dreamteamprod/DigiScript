import urllib

from tornado.web import URLSpec
import tornado.escape


class Route(object):
    """Decorator for assigning routes to Controllers"""

    _routes = []
    _formats = {}

    def __init__(self, route, name=None):
        self.route = route
        self.name = name
        self._formats[name] = route

    def __call__(self, controller):
        name = self.name or controller.__name__
        controller._route_name = name
        url_spec = URLSpec(self.route, controller, name=name)
        self._routes.append(url_spec)
        return controller

    @classmethod
    def routes(cls):
        return cls._routes

    @staticmethod
    def _url_escape(v):
        return urllib.quote(tornado.escape.utf8(v), '')

    @classmethod
    def make(cls, _name, **kwargs):
        if _name not in cls._formats:
            raise KeyError('No route by the name of `{}`'.format(_name))
        kwargs = {k: cls._url_escape(v) for k, v in kwargs.iteritems()}
        return cls._formats[_name] % kwargs
