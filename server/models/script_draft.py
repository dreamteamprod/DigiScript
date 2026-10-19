from __future__ import annotations

import datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db


if TYPE_CHECKING:
    from models.script import ScriptRevision
    from models.user import User


class ScriptDraft(db.Model):
    """Tracks an active collaborative editing draft for a script revision.

    :param id: Primary key.
    :param revision_id: Unique FK to the script revision being edited.
    :param data_path: Filesystem path to the serialized Y.Doc (.yjs file).
    :param created_at: When the draft was first created.
    :param last_modified: When the draft was last checkpointed to disk.
    :param last_editor_id: FK to the user who last made an edit.
    """

    __tablename__ = "script_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("script_revisions.id", ondelete="CASCADE"), unique=True
    )
    data_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    last_modified: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )
    last_editor_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    script_revision: Mapped[ScriptRevision] = relationship(foreign_keys=[revision_id])
    last_editor: Mapped[User] = relationship(foreign_keys=[last_editor_id])
