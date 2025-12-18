import datetime
import gzip
import json
import os
from functools import partial
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from tornado.ioloop import IOLoop

from digi_server.logger import get_logger
from models.models import db
from registry.schema import get_registry
from registry.user_overrides import UserOverridesRegistry
from utils.database import DeleteMixin


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer
    from models.cue import CueAssociation
    from models.show import Act, Character, CharacterGroup, Scene, Show


class Script(db.Model):
    __tablename__ = "script"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))
    current_revision: Mapped[int | None] = mapped_column(
        ForeignKey("script_revisions.id")
    )

    revisions: Mapped[List["ScriptRevision"]] = relationship(
        primaryjoin="ScriptRevision.script_id == Script.id", back_populates="script"
    )
    show: Mapped["Show"] = relationship(foreign_keys=[show_id])
    stage_direction_styles: Mapped[List["StageDirectionStyle"]] = relationship(
        cascade="all, delete-orphan", back_populates="script"
    )


class ScriptRevision(db.Model):
    __tablename__ = "script_revisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int | None] = mapped_column(ForeignKey("script.id"))

    revision: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    edited_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    description: Mapped[str | None] = mapped_column(String)
    previous_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("script_revisions.id", ondelete="SET NULL")
    )

    previous_revision: Mapped["ScriptRevision"] = relationship(
        foreign_keys=[previous_revision_id]
    )
    script: Mapped["Script"] = relationship(
        foreign_keys=[script_id], back_populates="revisions"
    )
    line_associations: Mapped[List["ScriptLineRevisionAssociation"]] = relationship(
        cascade="all, delete", back_populates="revision"
    )
    line_part_cuts: Mapped[List["ScriptCuts"]] = relationship(
        cascade="all, delete-orphan", back_populates="revision"
    )
    cue_associations: Mapped[List["CueAssociation"]] = relationship(
        cascade="all, delete-orphan", back_populates="revision"
    )


class ScriptLine(db.Model):
    __tablename__ = "script_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    act_id: Mapped[int | None] = mapped_column(ForeignKey("act.id"))
    scene_id: Mapped[int | None] = mapped_column(ForeignKey("scene.id"))
    page: Mapped[int | None] = mapped_column(index=True)
    stage_direction: Mapped[bool | None] = mapped_column(Boolean)
    stage_direction_style_id: Mapped[int | None] = mapped_column(
        ForeignKey("stage_direction_styles.id", ondelete="SET NULL")
    )

    act: Mapped["Act"] = relationship(back_populates="lines")
    scene: Mapped["Scene"] = relationship(back_populates="lines")
    revision_associations: Mapped[List["ScriptLineRevisionAssociation"]] = relationship(
        foreign_keys="[ScriptLineRevisionAssociation.line_id]",
        cascade="all, delete",
        back_populates="line",
    )
    cue_associations: Mapped[List["CueAssociation"]] = relationship(
        foreign_keys="[CueAssociation.line_id]", viewonly=True, back_populates="line"
    )
    line_parts: Mapped[List["ScriptLinePart"]] = relationship(
        cascade="all, delete-orphan", back_populates="line"
    )


class ScriptLineRevisionAssociation(db.Model, DeleteMixin):
    __tablename__ = "script_line_revision_association"

    revision_id: Mapped[int] = mapped_column(
        ForeignKey("script_revisions.id"), primary_key=True, index=True
    )
    line_id: Mapped[int] = mapped_column(
        ForeignKey("script_lines.id"), primary_key=True, index=True
    )

    next_line_id: Mapped[int | None] = mapped_column(ForeignKey("script_lines.id"))
    previous_line_id: Mapped[int | None] = mapped_column(ForeignKey("script_lines.id"))

    revision: Mapped["ScriptRevision"] = relationship(
        foreign_keys=[revision_id], back_populates="line_associations"
    )
    line: Mapped["ScriptLine"] = relationship(
        foreign_keys=[line_id], back_populates="revision_associations"
    )
    next_line: Mapped["ScriptLine"] = relationship(foreign_keys=[next_line_id])
    previous_line: Mapped["ScriptLine"] = relationship(foreign_keys=[previous_line_id])

    def pre_delete(self, session):
        pass

    @staticmethod
    def cleanup_orphaned_line(session, line_id, flush=True):
        """Helper method to check and delete orphaned ScriptLine objects.

        Can be called explicitly after deleting associations to ensure
        orphaned lines are cleaned up immediately.

        Args:
            session: Database session
            line_id: ID of the line to check for orphan status
            flush: Whether to flush before querying (default True).
                   Set to False when called from post_delete hooks.
        """
        # Local import to avoid circular dependency
        from models.cue import CueAssociation  # noqa: PLC0415

        # Flush to ensure pending operations are executed (if requested)
        if flush:
            session.flush()

        # Check all FK references using database queries
        line_id_refs = (
            session.scalar(
                select(func.count())
                .select_from(ScriptLineRevisionAssociation)
                .where(ScriptLineRevisionAssociation.line_id == line_id)
            )
            or 0
        )

        cue_refs = (
            session.scalar(
                select(func.count())
                .select_from(CueAssociation)
                .where(CueAssociation.line_id == line_id)
            )
            or 0
        )

        next_refs = (
            session.scalar(
                select(func.count())
                .select_from(ScriptLineRevisionAssociation)
                .where(ScriptLineRevisionAssociation.next_line_id == line_id)
            )
            or 0
        )

        prev_refs = (
            session.scalar(
                select(func.count())
                .select_from(ScriptLineRevisionAssociation)
                .where(ScriptLineRevisionAssociation.previous_line_id == line_id)
            )
            or 0
        )

        # Only delete if NO references remain
        if not line_id_refs and not cue_refs and not next_refs and not prev_refs:
            line = session.get(ScriptLine, line_id)
            if line:
                session.delete(line)

    def post_delete(self, session):
        # Delete orphaned lines after association is removed
        # Using post_delete avoids autoflush timing issues during cascade deletion
        # Using no_autoflush prevents lazy loading from triggering premature flush
        with session.no_autoflush:
            if self.line:
                # Use the static helper for consistent orphan cleanup logic
                # Don't flush during post_delete to avoid FK constraint errors mid-cascade
                ScriptLineRevisionAssociation.cleanup_orphaned_line(
                    session, self.line.id, flush=False
                )


class ScriptLinePart(db.Model):
    __tablename__ = "script_line_parts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    line_id: Mapped[int | None] = mapped_column(ForeignKey("script_lines.id"))

    part_index: Mapped[int | None] = mapped_column()
    character_id: Mapped[int | None] = mapped_column(ForeignKey("character.id"))
    character_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("character_group.id")
    )
    line_text: Mapped[str | None] = mapped_column(String)

    line: Mapped["ScriptLine"] = relationship(
        foreign_keys=[line_id], back_populates="line_parts"
    )
    character: Mapped["Character"] = relationship()
    character_group: Mapped["CharacterGroup"] = relationship()
    line_part_cuts: Mapped["ScriptCuts"] = relationship(
        cascade="all, delete-orphan", back_populates="line_part"
    )


class ScriptCuts(db.Model):
    __tablename__ = "script_line_cuts"

    line_part_id: Mapped[int] = mapped_column(
        ForeignKey("script_line_parts.id"), primary_key=True, index=True
    )
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("script_revisions.id"), primary_key=True, index=True
    )

    line_part: Mapped["ScriptLinePart"] = relationship(
        foreign_keys=[line_part_id], back_populates="line_part_cuts"
    )
    revision: Mapped["ScriptRevision"] = relationship(
        foreign_keys=[revision_id], back_populates="line_part_cuts"
    )


@UserOverridesRegistry.register(
    settings_fields=[
        "bold",
        "italic",
        "underline",
        "text_format",
        "text_colour",
        "enable_background_colour",
        "background_colour",
    ]
)
class StageDirectionStyle(db.Model, DeleteMixin):
    __tablename__ = "stage_direction_styles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int | None] = mapped_column(ForeignKey("script.id"), index=True)

    description: Mapped[str | None] = mapped_column(String)
    bold: Mapped[bool | None] = mapped_column(Boolean)
    italic: Mapped[bool | None] = mapped_column(Boolean)
    underline: Mapped[bool | None] = mapped_column(Boolean)
    text_format: Mapped[str | None] = mapped_column(String)
    text_colour: Mapped[str | None] = mapped_column(String)
    enable_background_colour: Mapped[bool | None] = mapped_column(Boolean)
    background_colour: Mapped[str | None] = mapped_column(String)

    script: Mapped["Script"] = relationship(
        foreign_keys=[script_id], back_populates="stage_direction_styles"
    )

    def pre_delete(self, session):
        from registry.user_overrides import (  # noqa: PLC0415
            UserOverridesRegistry,
        )

        UserOverridesRegistry.cleanup_overrides(session, self.__tablename__)

    def post_delete(self, session):
        pass


class CompiledScript(db.Model):
    __tablename__ = "compiled_scripts"

    revision_id: Mapped[int] = mapped_column(
        ForeignKey("script_revisions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )
    data_path: Mapped[str | None] = mapped_column(String)

    script_revision: Mapped["ScriptRevision"] = relationship(foreign_keys=[revision_id])

    @classmethod
    async def compile_script(cls, application: "DigiScriptServer", revision_id):
        line_schema = get_registry().get_schema_by_model(ScriptLine)()
        with application.get_db().sessionmaker() as session:
            revision: ScriptRevision = session.get(ScriptRevision, revision_id)
            if not revision:
                return

            line_ids_stmt = select(ScriptLineRevisionAssociation.line_id).where(
                ScriptLineRevisionAssociation.revision_id == revision.id
            )
            max_page = session.execute(
                select(func.max(ScriptLine.page)).where(
                    ScriptLine.id.in_(line_ids_stmt)
                )
            ).scalar()

            if max_page is None:
                max_page = 0

            page_info = {}
            current_page = 0
            while current_page != max_page:
                current_page += 1
                revision_lines: List[ScriptLineRevisionAssociation] = session.scalars(
                    select(ScriptLineRevisionAssociation).where(
                        ScriptLineRevisionAssociation.revision_id == revision.id,
                        ScriptLineRevisionAssociation.line.has(page=current_page),
                    )
                ).all()

                first_line = None
                for line in revision_lines:
                    if (
                        current_page == 1
                        and line.previous_line is None
                        or line.previous_line.page == current_page - 1
                    ):
                        if first_line:
                            get_logger().error("Failed to establish page line order")
                            return

                        first_line = line

                lines = []
                line_revision = first_line
                while line_revision:
                    if line_revision.line.page != current_page:
                        break

                    lines.append(line_schema.dump(line_revision.line))
                    line_revision = session.get(
                        ScriptLineRevisionAssociation,
                        (revision.id, line_revision.next_line_id),
                    )
                page_info[current_page] = lines

            # Save compiled script to disk
            file_name = f"script_{revision.script.show_id}_{revision.script_id}_{revision.id}.ds"
            scripts_path = await application.digi_settings.get("compiled_script_path")
            if not os.path.exists(scripts_path):
                os.makedirs(scripts_path)
            full_path = os.path.join(scripts_path, file_name)
            script_contents = json.dumps(page_info)
            with open(full_path, "wb") as file_pointer:
                file_pointer.write(gzip.compress(script_contents.encode("utf-8")))

            # Update/Create entry in table
            entry = session.get(cls, revision_id)
            if not entry:
                session.add(cls(revision_id=revision_id, data_path=full_path))
            else:
                entry.data_path = full_path
                entry.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
            session.commit()

    @classmethod
    def load_compiled_script(cls, application, revision_id):
        with application.get_db().sessionmaker() as session:
            revision: ScriptRevision = session.get(ScriptRevision, revision_id)
            if not revision:
                return {}
            compiled_script: cls = session.get(cls, revision.id)
            if not compiled_script:
                # Spawn a callback to create a compiled version of the script
                IOLoop.current().add_callback(
                    partial(cls.compile_script, application, revision.id)
                )
                return {}
            try:
                with open(compiled_script.data_path, "rb") as file_pointer:
                    data = json.loads(
                        gzip.decompress(file_pointer.read()).decode("utf-8")
                    )
            except FileNotFoundError:
                get_logger().warning(
                    f"Unable to open compiled script: {compiled_script.data_path}, file not found."
                )
                session.delete(compiled_script)
                session.commit()
                # Spawn a callback to create a compiled version of the script
                IOLoop.current().add_callback(
                    partial(cls.compile_script, application, revision.id)
                )
                return {}
            except Exception:
                get_logger().exception(
                    f"Unable to open compiled script: {compiled_script.data_path}, unhandled error."
                )
                session.delete(compiled_script)
                session.commit()
                # Spawn a callback to create a compiled version of the script
                IOLoop.current().add_callback(
                    partial(cls.compile_script, application, revision.id)
                )
                return {}
            return data
