from typing import List

from sqlalchemy import ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db
from models.script import ScriptLine, ScriptRevision
from registry.user_overrides import UserOverridesRegistry
from utils.database import DeleteMixin


@UserOverridesRegistry.register(settings_fields=["colour"])
class CueType(db.Model, DeleteMixin):
    __tablename__ = "cuetypes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))

    prefix: Mapped[str | None] = mapped_column(String(5))
    description: Mapped[str | None] = mapped_column(String(100))
    colour: Mapped[str | None] = mapped_column(String(16))

    cues: Mapped[List["Cue"]] = relationship(
        back_populates="cue_type", cascade="all, delete-orphan"
    )

    def pre_delete(self, session):
        UserOverridesRegistry.cleanup_overrides(session, self.__tablename__)

    def post_delete(self, session):
        pass


class Cue(db.Model):
    __tablename__ = "cue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cue_type_id: Mapped[int | None] = mapped_column(ForeignKey("cuetypes.id"))
    ident: Mapped[str | None] = mapped_column(String(50))

    cue_type: Mapped["CueType"] = relationship(
        foreign_keys=[cue_type_id], back_populates="cues"
    )
    revision_associations: Mapped[List["CueAssociation"]] = relationship(
        cascade="all, delete-orphan", back_populates="cue"
    )


class CueAssociation(db.Model, DeleteMixin):
    __tablename__ = "script_cue_association"

    revision_id: Mapped[int] = mapped_column(
        ForeignKey("script_revisions.id"), primary_key=True, index=True
    )
    line_id: Mapped[int] = mapped_column(
        ForeignKey("script_lines.id"), primary_key=True, index=True
    )
    cue_id: Mapped[int] = mapped_column(
        ForeignKey("cue.id"), primary_key=True, index=True
    )

    revision: Mapped["ScriptRevision"] = relationship(
        foreign_keys=[revision_id], back_populates="cue_associations"
    )
    line: Mapped["ScriptLine"] = relationship(
        foreign_keys=[line_id], back_populates="cue_associations", viewonly=True
    )
    cue: Mapped["Cue"] = relationship(
        foreign_keys=[cue_id], back_populates="revision_associations"
    )

    @staticmethod
    def cleanup_orphaned_cue(session, cue_id, flush=True):
        """Helper method to check and delete orphaned Cue objects.

        Can be called explicitly after deleting associations to ensure
        orphaned cues are cleaned up immediately.

        Args:
            session: Database session
            cue_id: ID of the cue to check for orphan status
            flush: Whether to flush before querying (default True).
                   Set to False when called from post_delete hooks.
        """
        # Flush to ensure pending operations are executed (if requested)
        if flush:
            session.flush()

        # Check cue_id references using database query
        cue_assoc_refs = (
            session.scalar(
                select(func.count())
                .select_from(CueAssociation)
                .where(CueAssociation.cue_id == cue_id)
            )
            or 0
        )

        # Only delete if NO references remain
        if not cue_assoc_refs:
            cue = session.get(Cue, cue_id)
            if cue:
                session.delete(cue)

    def pre_delete(self, session):
        pass

    def post_delete(self, session):
        # Delete orphaned cues after association is removed
        # Using post_delete avoids autoflush timing issues during cascade deletion
        # Using no_autoflush prevents lazy loading from triggering premature flush
        with session.no_autoflush:
            if self.cue:
                # Use the static helper for consistent orphan cleanup logic
                # Don't flush during post_delete to avoid FK constraint errors mid-cascade
                CueAssociation.cleanup_orphaned_cue(session, self.cue.id, flush=False)
