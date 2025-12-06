import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, Date, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db


if TYPE_CHECKING:
    from models.cue import CueType
    from models.mics import MicrophoneAllocation
    from models.script import ScriptLine
    from models.session import ShowSession


class Show(db.Model):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[datetime.date | None] = mapped_column(Date())
    end_date: Mapped[datetime.date | None] = mapped_column(Date())
    created_at: Mapped[datetime.datetime | None] = mapped_column()
    edited_at: Mapped[datetime.datetime | None] = mapped_column()
    first_act_id: Mapped[int | None] = mapped_column(ForeignKey("act.id"))
    current_session_id: Mapped[int | None] = mapped_column(ForeignKey("showsession.id"))

    # Relationships
    first_act: Mapped["Act"] = relationship(foreign_keys=[first_act_id])
    current_session: Mapped["ShowSession"] = relationship(
        foreign_keys=[current_session_id]
    )

    cast_list: Mapped[List["Cast"]] = relationship(cascade="all, delete-orphan")
    character_list: Mapped[List["Character"]] = relationship(
        cascade="all, delete-orphan"
    )
    character_group_list: Mapped[List["CharacterGroup"]] = relationship(
        cascade="all, delete-orphan"
    )
    act_list: Mapped[List["Act"]] = relationship(
        primaryjoin="Show.id == Act.show_id", cascade="all, delete-orphan"
    )
    scene_list: Mapped[List["Scene"]] = relationship(cascade="all, delete-orphan")
    cue_type_list: Mapped[List["CueType"]] = relationship(cascade="all, delete-orphan")


class Cast(db.Model):
    __tablename__ = "cast"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))
    first_name: Mapped[str | None] = mapped_column()
    last_name: Mapped[str | None] = mapped_column()

    # Relationships
    character_list: Mapped[List["Character"]] = relationship(
        back_populates="cast_member"
    )


character_group_association_table = Table(
    "character_group_association",
    db.Model.metadata,
    Column("character_group_id", ForeignKey("character_group.id"), primary_key=True),
    Column("character_id", ForeignKey("character.id"), primary_key=True),
)


class Character(db.Model):
    __tablename__ = "character"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))
    played_by: Mapped[int | None] = mapped_column(ForeignKey("cast.id"))
    name: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    cast_member: Mapped["Cast"] = relationship(back_populates="character_list")
    character_groups: Mapped[List["CharacterGroup"]] = relationship(
        secondary=character_group_association_table,
        back_populates="characters",
    )
    mic_allocations: Mapped[List["MicrophoneAllocation"]] = relationship(
        cascade="all, delete-orphan", back_populates="character"
    )


class CharacterGroup(db.Model):
    __tablename__ = "character_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))

    name: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    characters: Mapped[List["Character"]] = relationship(
        secondary=character_group_association_table,
        back_populates="character_groups",
    )


class Act(db.Model):
    __tablename__ = "act"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))
    name: Mapped[str | None] = mapped_column()
    interval_after: Mapped[bool | None] = mapped_column()
    first_scene_id: Mapped[int | None] = mapped_column(ForeignKey("scene.id"))
    previous_act_id: Mapped[int | None] = mapped_column(ForeignKey("act.id"))

    first_scene: Mapped["Scene"] = relationship(foreign_keys=[first_scene_id])
    previous_act: Mapped["Act"] = relationship(
        remote_side="[Act.id]",
        back_populates="next_act",
        foreign_keys=[previous_act_id],
    )
    next_act: Mapped["Act"] = relationship(
        back_populates="previous_act",
        foreign_keys="[Act.previous_act_id]",
    )
    scene_list: Mapped[List["Scene"]] = relationship(
        back_populates="act",
        cascade="all, delete-orphan",
        foreign_keys="[Scene.act_id]",
    )
    lines: Mapped[List["ScriptLine"]] = relationship(
        back_populates="act", cascade="all, delete-orphan"
    )


class Scene(db.Model):
    __tablename__ = "scene"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id"))
    act_id: Mapped[int | None] = mapped_column(ForeignKey("act.id"))
    name: Mapped[str | None] = mapped_column()
    previous_scene_id: Mapped[int | None] = mapped_column(ForeignKey("scene.id"))

    act: Mapped["Act"] = relationship(
        back_populates="scene_list",
        foreign_keys=[act_id],
        post_update=True,
    )
    previous_scene: Mapped["Scene"] = relationship(
        remote_side="[Scene.id]",
        back_populates="next_scene",
        foreign_keys=[previous_scene_id],
    )
    next_scene: Mapped["Scene"] = relationship(
        back_populates="previous_scene",
        foreign_keys="[Scene.previous_scene_id]",
    )
    lines: Mapped[List["ScriptLine"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )
    mic_allocations: Mapped[List["MicrophoneAllocation"]] = relationship(
        cascade="all, delete-orphan", back_populates="scene"
    )
