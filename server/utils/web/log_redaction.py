"""Key-based redaction of secrets from structured data before it is logged."""

from __future__ import annotations

from typing import Any


REDACTED = "<-- REDACTED -->"

# Lower-cased dict keys whose values must never reach a log file.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "new_password",
        "old_password",
        "current_password",
        "token",
        "access_token",
        "refresh_token",
        "api_token",
        "secret",
    }
)


def redact_sensitive_keys(value: Any) -> Any:
    """Return a copy of *value* with the values of sensitive keys replaced.

    Recurses through dicts and lists. Key matching is case-insensitive. The input
    is not modified.

    :param value: Decoded JSON data (dict, list or scalar).
    :returns: A redacted copy.
    """
    if isinstance(value, dict):
        return {
            key: (
                REDACTED
                if isinstance(key, str) and key.lower() in SENSITIVE_KEYS
                else redact_sensitive_keys(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_keys(item) for item in value]
    return value
