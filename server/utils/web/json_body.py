from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tornado import escape
from tornado.web import HTTPError


if TYPE_CHECKING:
    from tornado.web import RequestHandler


def get_json_object(handler: RequestHandler) -> dict[str, Any]:
    """Decode the request body as a JSON object.

    :param handler: The request handler whose body should be decoded.
    :returns: The decoded JSON object.
    :raises HTTPError: With status 400 if the body is not valid JSON, or the
        decoded value is not a JSON object (dict).
    """
    try:
        data = escape.json_decode(handler.request.body)
    except (ValueError, TypeError) as exc:
        raise HTTPError(400, log_message="Invalid JSON body") from exc
    if not isinstance(data, dict):
        raise HTTPError(400, log_message="JSON body must be an object")
    return data
