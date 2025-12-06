from typing import List

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    def pre_delete(self, session):
        if len(self.cue.revision_associations) == 1:
            session.delete(self.cue)

    def post_delete(self, session):
        pass
