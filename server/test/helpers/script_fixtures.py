"""Shared test fixture helpers for script/revision-related tests.

These helpers reduce duplication across test setUp methods that need
Show / Script / ScriptRevision scaffolding.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock

from models.script import Script, ScriptRevision
from models.show import Show, ShowScriptType


def create_show_script_revision(session, description="Test Rev"):
    """Create a Show, Script, and an initial current ScriptRevision.

    :param session: SQLAlchemy session.
    :param description: Description for the created revision.
    :returns: Tuple of (show, script, revision) ORM objects.
    """
    show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
    session.add(show)
    session.flush()

    script = Script(show_id=show.id)
    session.add(script)
    session.flush()

    revision = ScriptRevision(script_id=script.id, revision=1, description=description)
    session.add(revision)
    session.flush()
    script.current_revision = revision.id

    return show, script, revision


@contextmanager
def mock_active_room(app, **room_attrs):
    """Patch ``app.room_manager`` so ``get_active_room()`` returns a mock room.

    :param app: The application instance (``self._app`` in a test).
    :param room_attrs: Attributes to set on the mock room, e.g. ``has_editors=True``.
    :yields: The mock room, in case a test needs to assert against it.
    """
    mock_room = MagicMock()
    for name, value in room_attrs.items():
        setattr(mock_room, name, value)
    mock_manager = MagicMock()
    mock_manager.get_active_room.return_value = mock_room
    app.room_manager = mock_manager

    try:
        yield mock_room
    finally:
        del app.room_manager
