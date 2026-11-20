from __future__ import annotations

from tornado.web import RequestHandler, StaticFileHandler


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "same-origin",
}


def apply_security_headers(handler: RequestHandler) -> None:
    """Set the baseline security headers on a handler's response.

    No Content-Security-Policy is set: the SPA and the bundled docs rely on
    inline styles/scripts, so a policy strict enough to be useful would break them.

    :param handler: The request handler whose response should carry the headers.
    """
    for name, value in SECURITY_HEADERS.items():
        handler.set_header(name, value)


class SecureStaticFileHandler(StaticFileHandler):
    """A ``StaticFileHandler`` that also sends the baseline security headers."""

    def set_default_headers(self) -> None:
        apply_security_headers(self)
