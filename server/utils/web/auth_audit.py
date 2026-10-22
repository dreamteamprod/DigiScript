"""Audit logging and metrics for authentication events.

Every security-relevant authentication action (login, logout, password change
and reset, token refresh, API token generation and revocation) is recorded
through :func:`audit`. Each call emits a single line on the ``DigiScript.Audit``
logger and increments the ``digiscript_auth_events_total`` Prometheus counter.

Secrets (passwords, tokens, API keys) must never be passed to this module.
Attacker-controlled strings (notably the username supplied to the login
endpoint) are sanitised before they are logged, and the metric labels are drawn
from fixed sets, so a client cannot inject log lines or create unbounded label
cardinality.

The counter is module-level so it is registered exactly once per process,
however many application instances are created (tests create many).
"""

from __future__ import annotations

import json
import logging
import unicodedata
from typing import Optional

from prometheus_client import Counter

from digi_server.logger import get_logger


EVENTS = frozenset(
    {
        "login",
        "logout",
        "password_change",
        "password_reset",
        "token_refresh",
        "api_token_generate",
        "api_token_revoke",
        "user_create",
        "user_update",
        "user_delete",
    }
)
RESULTS = frozenset({"success", "failure"})

MAX_FIELD_LENGTH = 64

auth_events_total = Counter(
    name="digiscript_auth_events_total",
    documentation="Authentication events by type and outcome",
    labelnames=("event", "result"),
)


def sanitise(value: object, max_length: int = MAX_FIELD_LENGTH) -> str:
    """Make an untrusted value safe to embed in a single log line.

    Control and other non-printable characters (including newlines) are removed
    and the result is truncated to *max_length* characters.

    :param value: The value to sanitise; converted with ``str``.
    :param max_length: Maximum number of characters kept.
    :returns: The sanitised string.
    """
    text = "".join(ch for ch in str(value) if unicodedata.category(ch)[0] != "C")
    return text[:max_length]


def actor(controller) -> dict:
    """Return the ``audit`` keyword arguments identifying a request's actor.

    :param controller: A request handler with ``current_user`` and ``request``.
    :returns: ``username``, ``user_id`` and ``remote_ip`` for the caller (the
        first two are ``None`` when the request is unauthenticated).
    """
    user = controller.current_user or {}
    return {
        "username": user.get("username"),
        "user_id": user.get("id"),
        "remote_ip": controller.request.remote_ip,
    }


def audit(
    event: str,
    result: str,
    *,
    username: Optional[str] = None,
    user_id: Optional[int] = None,
    remote_ip: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Record an authentication event in the log and the metrics.

    Successes are logged at INFO and failures at WARNING on
    ``DigiScript.Audit``. The ``detail`` is a short reason or context string
    (for example ``reason=bad_password``); it must not contain secrets.

    :param event: One of :data:`EVENTS`.
    :param result: ``"success"`` or ``"failure"``.
    :param username: Username the event concerns (sanitised before logging).
    :param user_id: Database id of that user, if known.
    :param remote_ip: Client IP address.
    :param detail: Optional short context, sanitised before logging.
    :raises ValueError: If ``event`` or ``result`` is not a known value.
    """
    if event not in EVENTS or result not in RESULTS:
        raise ValueError(f"Unknown audit event/result: {event!r}/{result!r}")

    auth_events_total.labels(event=event, result=result).inc()

    safe_username = sanitise(username) if username is not None else None
    parts = [f"AUDIT {event} {result}"]
    if safe_username is not None:
        # JSON-quoted so spaces in a hostile name cannot spoof other fields.
        parts.append(f"username={json.dumps(safe_username)}")
    if user_id is not None:
        parts.append(f"user_id={user_id}")
    if remote_ip:
        parts.append(f"ip={sanitise(remote_ip)}")
    if detail:
        parts.append(sanitise(detail, 128))

    extra: dict = {}
    if safe_username is not None:
        extra["username"] = safe_username
    if user_id is not None:
        extra["user_id"] = user_id
    if remote_ip:
        extra["remote_ip"] = remote_ip

    level = logging.INFO if result == "success" else logging.WARNING
    get_logger("Audit").log(level, " ".join(parts), extra=extra)
