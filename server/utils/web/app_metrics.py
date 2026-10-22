"""Prometheus gauges and counters answering "is the show healthy?".

The metric objects are module-level singletons, so each series is registered
with Prometheus exactly once per process however many application instances are
created (tests create many). The room managers and applications the live gauges
read from are a different matter: each instance registers itself in a weak set,
so several can be tracked at once and they drop out when garbage collected.
Every collect-time callback is guarded so that one failing gauge can never break
the ``/debug/metrics`` scrape. The series are exposed alongside the others at
``/debug/metrics``:

* ``digiscript_ws_connections`` - currently open WebSocket connections.
* ``digiscript_ws_messages_total{op}`` - inbound WebSocket messages by OP. The
  OP is client-controlled, so only the OPs the server knows are used as label
  values; anything else is reported as ``OTHER``.
* ``digiscript_collab_rooms`` - active collaborative script rooms, read live
  from the registered room managers at scrape time so it cannot drift.
* ``digiscript_show_session_active`` - 1 while a live show session is running,
  read live from the database at scrape time.
* ``digiscript_info{version}`` - constant 1 carrying the application version.
"""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge

from digi_server.logger import get_logger
from digi_server.settings import get_version
from models.show import Show


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer
    from utils.script_room_manager import RoomManager


OTHER_OP = "OTHER"

ws_connections = Gauge(
    "digiscript_ws_connections", "Currently open WebSocket connections"
)

ws_messages_total = Counter(
    "digiscript_ws_messages_total",
    "Inbound WebSocket messages by OP (unknown OPs are reported as OTHER)",
    labelnames=("op",),
)

collab_rooms = Gauge(
    "digiscript_collab_rooms", "Currently active collaborative script rooms"
)

show_session_active = Gauge(
    "digiscript_show_session_active",
    "1 if a live show session is running, otherwise 0",
)

app_info = Gauge(
    "digiscript_info", "DigiScript application information", labelnames=("version",)
)

_room_managers: weakref.WeakSet = weakref.WeakSet()
_applications: weakref.WeakSet = weakref.WeakSet()


def bounded_op(op: str, known_ops) -> str:
    """Return ``op`` if the server knows it, else ``OTHER``.

    :param op: The OP taken from a client message.
    :param known_ops: Collection of OPs allowed as label values.
    :returns: A label value from a fixed, finite set.
    """
    return op if op in known_ops else OTHER_OP


def register_room_manager(manager: RoomManager) -> None:
    """Include ``manager``'s active room in ``digiscript_collab_rooms``.

    :param manager: The room manager to count.
    """
    _room_managers.add(manager)


def register_application(app: DigiScriptServer) -> None:
    """Include ``app``'s live show session in ``digiscript_show_session_active``.

    :param app: The application server.
    """
    _applications.add(app)


def register_app_info() -> None:
    """Set ``digiscript_info`` for the running version (idempotent)."""
    app_info.labels(get_version()).set(1)


def _count_rooms() -> float:
    """Count active rooms across registered managers, skipping any that fail."""
    count = 0
    for manager in _room_managers:
        try:
            if manager.get_active_room():
                count += 1
        except Exception:
            get_logger().warning(
                f"Could not read the active room of {type(manager).__name__} "
                f"for metrics",
                exc_info=True,
            )
    return float(count)


def _app_has_live_session(app: DigiScriptServer) -> bool:
    show_id = app.digi_settings.get_sync("current_show")
    if not show_id:
        return False
    with app.get_db().sessionmaker() as session:
        show = session.get(Show, show_id)
        return bool(show and show.current_session_id)


def _live_session_value() -> float:
    """Return 1 if any registered app has a live session, else 0.

    Each app is checked independently; one that fails is logged (with its type
    and id) and skipped. The value is NaN only if no app could be read and at
    least one failed, so a failure is never reported as a confident 0.
    """
    active = False
    failed = 0
    for app in _applications:
        try:
            # Evaluate every app (no short-circuit) so a failing app is always
            # logged, whatever order the weak set happens to iterate in.
            has_live_session = _app_has_live_session(app)
            active = active or has_live_session
        except Exception:
            failed += 1
            get_logger().warning(
                f"Could not determine live show session state of "
                f"{type(app).__name__} {id(app):#x} for metrics",
                exc_info=True,
            )
    if not active and failed:
        return float("nan")
    return 1.0 if active else 0.0


collab_rooms.set_function(_count_rooms)
show_session_active.set_function(_live_session_value)
register_app_info()
