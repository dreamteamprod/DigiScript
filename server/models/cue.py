from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from models.models import db
from models.script import ScriptLine, ScriptRevision
from utils.database import DeleteMixin


class CueType(db.Model):
    __tablename__ = "cuetypes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))

    prefix = Column(String(5))
    description = Column(String(100))
    colour = Column(String())

    cues = relationship("Cue", back_populates="cue_type", cascade="all, delete-orphan")


class Cue(db.Model):
    __tablename__ = "cue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cue_type_id = Column(Integer, ForeignKey("cuetypes.id"))
    ident = Column(String())

    cue_type = relationship(
        "CueType", uselist=False, foreign_keys=[cue_type_id], back_populates="cues"
    )


class CueAssociation(db.Model, DeleteMixin):
    __tablename__ = "script_cue_association"
    __mapper_args__ = {"confirm_deleted_rows": False}

    revision_id = Column(
        Integer, ForeignKey("script_revisions.id"), primary_key=True, index=True
    )
    line_id = Column(
        Integer, ForeignKey("script_lines.id"), primary_key=True, index=True
    )
    cue_id = Column(Integer, ForeignKey("cue.id"), primary_key=True, index=True)

    revision: ScriptRevision = relationship(
        "ScriptRevision",
        foreign_keys=[revision_id],
        uselist=False,
        backref=backref("cue_associations", uselist=True, cascade="all, delete-orphan"),
    )
    line: ScriptLine = relationship(
        "ScriptLine",
        foreign_keys=[line_id],
        uselist=False,
        backref=backref("cue_associations", uselist=True, viewonly=True),
    )
    cue: Cue = relationship(
        "Cue",
        foreign_keys=[cue_id],
        uselist=False,
        backref=backref(
            "revision_associations", uselist=True, cascade="all, delete-orphan"
        ),
    )

    def pre_delete(self, session):
        if len(self.cue.revision_associations) == 1:
            session.delete(self.cue)

    def post_delete(self, session):
        pass
