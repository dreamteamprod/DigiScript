"""Key-based redaction of secrets from structured data before it is logged."""

from __future__ import annotations

from typing import Any

from jsonpath import JSONPatch, JSONPatchError


REDACTED = "<-- REDACTED -->"

# Lower-cased dict keys whose values must never reach a log file.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "confirmpassword",
        "confirm_password",
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


def apply_path_redactions(patch: JSONPatch, body: Any) -> None:
    """Apply each operation of a redaction *patch* to *body* independently, in place.

    A path absent from the body is skipped without stopping the remaining paths
    (``JSONPatch.apply`` would abort at the first failure). Bodies that are not a
    dict or list are left alone: ``JSONPatch`` would treat a string as serialized
    JSON and raise on it.

    :param patch: Patch of ``replace`` operations built by ``redact_data_paths``.
    :param body: Decoded JSON request body, modified in place.
    """
    if not isinstance(body, (dict, list)):
        return
    for operation in patch.ops:
        single = JSONPatch()
        single.ops.append(operation)
        try:
            single.apply(body)
        except JSONPatchError:
            continue
