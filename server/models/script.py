import datetime
import gzip
import json
import os
from functools import partial
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import backref, relationship
from tornado.ioloop import IOLoop

from digi_server.logger import get_logger
from models.models import db
from models.user import UserOverrides
from registry.schema import get_registry
from registry.user_overrides import UserOverridesRegistry
from utils.database import DeleteMixin

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class Script(db.Model):
    __tablename__ = "script"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    current_revision = Column(Integer, ForeignKey("script_revisions.id"))

    revisions = relationship(
        "ScriptRevision",
        uselist=True,
        primaryjoin="ScriptRevision.script_id == Script.id",
        back_populates="script",
    )
    show = relationship("Show", foreign_keys=[show_id])


class ScriptRevision(db.Model):
    __tablename__ = "script_revisions"
    __mapper_args__ = {"confirm_deleted_rows": False}

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("script.id"))

    revision = Column(Integer)
    created_at = Column(DateTime)
    edited_at = Column(DateTime)
    description = Column(String)
    previous_revision_id = Column(
        Integer, ForeignKey("script_revisions.id", ondelete="SET NULL")
    )

    previous_revision = relationship(
        "ScriptRevision", foreign_keys=[previous_revision_id]
    )
    script = relationship("Script", foreign_keys=[script_id])


class ScriptLine(db.Model):
    __tablename__ = "script_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    act_id = Column(Integer, ForeignKey("act.id"))
    scene_id = Column(Integer, ForeignKey("scene.id"))
    page = Column(Integer, index=True)
    stage_direction = Column(Boolean)
    stage_direction_style_id = Column(
        Integer, ForeignKey("stage_direction_styles.id", ondelete="SET NULL")
    )

    act = relationship("Act", uselist=False, back_populates="lines")
    scene = relationship("Scene", uselist=False, back_populates="lines")


class ScriptLineRevisionAssociation(db.Model, DeleteMixin):
    __tablename__ = "script_line_revision_association"
    __mapper_args__ = {"confirm_deleted_rows": False}

    revision_id = Column(
        Integer, ForeignKey("script_revisions.id"), primary_key=True, index=True
    )
    line_id = Column(
        Integer,
        ForeignKey("script_lines.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    next_line_id = Column(Integer, ForeignKey("script_lines.id", ondelete="CASCADE"))
    previous_line_id = Column(
        Integer, ForeignKey("script_lines.id", ondelete="CASCADE")
    )

    revision: ScriptRevision = relationship(
        "ScriptRevision",
        foreign_keys=[revision_id],
        uselist=False,
        backref=backref("line_associations", uselist=True, cascade="all, delete"),
    )
    line: ScriptLine = relationship(
        "ScriptLine",
        foreign_keys=[line_id],
        uselist=False,
        backref=backref("revision_associations", uselist=True, cascade="all, delete"),
    )
    next_line: ScriptLine = relationship("ScriptLine", foreign_keys=[next_line_id])
    previous_line: ScriptLine = relationship(
        "ScriptLine", foreign_keys=[previous_line_id]
    )

    def pre_delete(self, session):
        if self.line and len(self.line.revision_associations) == 1:
            session.delete(self.line)

    def post_delete(self, session):
        pass


class ScriptLinePart(db.Model):
    __tablename__ = "script_line_parts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(Integer, ForeignKey("script_lines.id", ondelete="CASCADE"))

    part_index = Column(Integer)
    character_id = Column(Integer, ForeignKey("character.id"))
    character_group_id = Column(Integer, ForeignKey("character_group.id"))
    line_text = Column(String)

    line = relationship(
        "ScriptLine",
        uselist=False,
        foreign_keys=[line_id],
        backref=backref("line_parts", uselist=True, cascade="all, delete-orphan"),
    )
    character = relationship("Character", uselist=False)
    character_group = relationship("CharacterGroup", uselist=False)


class ScriptCuts(db.Model):
    __tablename__ = "script_line_cuts"

    line_part_id = Column(
        Integer, ForeignKey("script_line_parts.id"), primary_key=True, index=True
    )
    revision_id = Column(
        Integer, ForeignKey("script_revisions.id"), primary_key=True, index=True
    )

    line_part = relationship(
        "ScriptLinePart",
        uselist=False,
        foreign_keys=[line_part_id],
        backref=backref("line_part_cuts", uselist=False, cascade="all, delete-orphan"),
    )
    revision = relationship(
        "ScriptRevision",
        uselist=False,
        foreign_keys=[revision_id],
        backref=backref("line_part_cuts", uselist=True, cascade="all, delete-orphan"),
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("script.id"), index=True)

    description = Column(String)
    bold = Column(Boolean)
    italic = Column(Boolean)
    underline = Column(Boolean)
    text_format = Column(String)
    text_colour = Column(String)
    enable_background_colour = Column(Boolean)
    background_colour = Column(String)

    script = relationship(
        "Script",
        uselist=False,
        foreign_keys=[script_id],
        backref=backref(
            "stage_direction_styles", uselist=True, cascade="all, delete-orphan"
        ),
    )

    def pre_delete(self, session):
        user_overrides = (
            session.query(UserOverrides)
            .filter(UserOverrides.settings_type == self.__tablename__)
            .all()
        )
        for override in user_overrides:
            session.delete(override)

    def post_delete(self, session):
        pass


class CompiledScript(db.Model):
    __tablename__ = "compiled_scripts"

    revision_id = Column(
        Integer, ForeignKey("script_revisions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = Column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    updated_at = Column(
        DateTime,
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )
    data_path = Column(String)

    script_revision = relationship("ScriptRevision", foreign_keys=[revision_id])

    @classmethod
    async def compile_script(cls, application: "DigiScriptServer", revision_id):
        line_schema = get_registry().get_schema_by_model(ScriptLine)()
        with application.get_db().sessionmaker() as session:
            revision: ScriptRevision = session.get(ScriptRevision, revision_id)
            if not revision:
                return

            line_ids = (
                session.query(ScriptLineRevisionAssociation)
                .with_entities(ScriptLineRevisionAssociation.line_id)
                .filter(ScriptLineRevisionAssociation.revision_id == revision.id)
            )
            max_page = (
                session.query(ScriptLine)
                .with_entities(func.max(ScriptLine.page))
                .where(ScriptLine.id.in_(line_ids))
                .first()[0]
            )

            if max_page is None:
                max_page = 0

            page_info = {}
            current_page = 0
            while current_page != max_page:
                current_page += 1
                revision_lines: List[ScriptLineRevisionAssociation] = (
                    session.query(ScriptLineRevisionAssociation)
                    .filter(
                        ScriptLineRevisionAssociation.revision_id == revision.id,
                        ScriptLineRevisionAssociation.line.has(page=current_page),
                    )
                    .all()
                )

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
                    line_revision = session.query(ScriptLineRevisionAssociation).get(
                        {
                            "revision_id": revision.id,
                            "line_id": line_revision.next_line_id,
                        }
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
