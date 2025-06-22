from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import backref, relationship

from models.models import db


class Show(db.Model):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    start_date = Column(Date())
    end_date = Column(Date())
    created_at = Column(DateTime())
    edited_at = Column(DateTime())
    first_act_id = Column(Integer, ForeignKey("act.id"))
    current_session_id = Column(Integer, ForeignKey("showsession.id"))

    # Relationships
    first_act = relationship("Act", uselist=False, foreign_keys=[first_act_id])
    current_session = relationship(
        "ShowSession", uselist=False, foreign_keys=[current_session_id]
    )

    cast_list = relationship("Cast", cascade="all, delete-orphan")
    crew_list = relationship("Crew", cascade="all, delete-orphan")
    scenery_list = relationship("Scenery", cascade="all, delete-orphan")
    props_list = relationship("Props", cascade="all, delete-orphan")
    character_list = relationship("Character", cascade="all, delete-orphan")
    character_group_list = relationship("CharacterGroup", cascade="all, delete-orphan")
    act_list = relationship(
        "Act", primaryjoin=lambda: Show.id == Act.show_id, cascade="all, delete-orphan"
    )
    scene_list = relationship("Scene", cascade="all, delete-orphan")
    cue_type_list = relationship("CueType", cascade="all, delete-orphan")


class Cast(db.Model):
    __tablename__ = "cast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    first_name = Column(String)
    last_name = Column(String)

    # Relationships
    character_list = relationship("Character", back_populates="cast_member")


character_group_association_table = Table(
    "character_group_association",
    db.Model.metadata,
    Column("character_group_id", ForeignKey("character_group.id"), primary_key=True),
    Column("character_id", ForeignKey("character.id"), primary_key=True),
)


class Character(db.Model):
    __tablename__ = "character"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    played_by = Column(Integer, ForeignKey("cast.id"))
    name = Column(String)
    description = Column(String)

    cast_member = relationship("Cast", back_populates="character_list")
    character_groups = relationship(
        "CharacterGroup",
        secondary=character_group_association_table,
        back_populates="characters",
    )


class CharacterGroup(db.Model):
    __tablename__ = "character_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))

    name = Column(String)
    description = Column(String)

    characters = relationship(
        "Character",
        secondary=character_group_association_table,
        back_populates="character_groups",
    )


class Act(db.Model):
    __tablename__ = "act"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    name = Column(String)
    interval_after = Column(Boolean)
    first_scene_id = Column(Integer, ForeignKey("scene.id"))
    previous_act_id = Column(Integer, ForeignKey("act.id"))

    first_scene = relationship("Scene", uselist=False, foreign_keys=[first_scene_id])
    previous_act = relationship(
        "Act",
        uselist=False,
        remote_side=[id],
        backref=backref("next_act", uselist=False),
    )
    lines = relationship(
        "ScriptLine", back_populates="act", cascade="all, delete-orphan"
    )


class Scene(db.Model):
    __tablename__ = "scene"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    act_id = Column(Integer, ForeignKey("act.id"))
    name = Column(String)
    previous_scene_id = Column(Integer, ForeignKey("scene.id"))

    act = relationship(
        "Act",
        uselist=False,
        backref=backref("scene_list", cascade="all, delete-orphan"),
        foreign_keys=[act_id],
        post_update=True,
    )
    previous_scene = relationship(
        "Scene",
        uselist=False,
        remote_side=[id],
        backref=backref("next_scene", uselist=False),
    )
    lines = relationship(
        "ScriptLine", back_populates="scene", cascade="all, delete-orphan"
    )
    # scenery_allocations = relationship("Scenery", back_populates="scene")
    # props_allocations = relationship("Props", back_populates="scene")
