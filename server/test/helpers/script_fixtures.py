"""Shared test fixture helpers for script/revision-related tests.

These helpers reduce duplication across test setUp methods that need
Show / Script / ScriptRevision scaffolding.
"""

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
