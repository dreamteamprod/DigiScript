from __future__ import annotations

from typing import List

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db
from models.show import Scene, Show


class Crew(db.Model):
    __tablename__ = "crew"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str | None] = mapped_column()

    show: Mapped[Show] = relationship(back_populates="crew_list")


class SceneryAllocation(db.Model):
    __tablename__ = "scenery_allocation"
    __table_args__ = (
        UniqueConstraint("scenery_id", "scene_id", name="uq_scenery_scene"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenery_id: Mapped[int] = mapped_column(
        ForeignKey("scenery.id", ondelete="CASCADE")
    )
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"))

    scenery: Mapped[Scenery] = relationship(
        back_populates="scene_allocations",
        foreign_keys=[scenery_id],
    )
    scene: Mapped[Scene] = relationship(
        back_populates="scenery_allocations",
        foreign_keys=[scene_id],
    )


class PropsAllocation(db.Model):
    __tablename__ = "props_allocation"
    __table_args__ = (UniqueConstraint("props_id", "scene_id", name="uq_props_scene"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    props_id: Mapped[int] = mapped_column(ForeignKey("props.id", ondelete="CASCADE"))
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"))

    prop: Mapped[Props] = relationship(
        back_populates="scene_allocations",
        foreign_keys=[props_id],
    )
    scene: Mapped[Scene] = relationship(
        back_populates="props_allocations",
        foreign_keys=[scene_id],
    )


class SceneryType(db.Model):
    __tablename__ = "scenery_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped[Show] = relationship(back_populates="scenery_types")
    scenery_items: Mapped[list[Scenery]] = relationship(
        back_populates="scenery_type",
        cascade="all, delete-orphan",
    )


class Scenery(db.Model):
    __tablename__ = "scenery"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    scenery_type_id: Mapped[int] = mapped_column(ForeignKey("scenery_type.id"))
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped[Show] = relationship(back_populates="scenery_list")
    scenery_type: Mapped[SceneryType] = relationship(back_populates="scenery_items")
    scene_allocations: Mapped[List[SceneryAllocation]] = relationship(
        back_populates="scenery",
        cascade="all, delete-orphan",
    )


class PropType(db.Model):
    __tablename__ = "prop_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped[Show] = relationship(back_populates="prop_types")
    prop_items: Mapped[List[Props]] = relationship(
        back_populates="prop_type",
        cascade="all, delete-orphan",
    )


class Props(db.Model):
    __tablename__ = "props"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    prop_type_id: Mapped[int] = mapped_column(ForeignKey("prop_type.id"))
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped[Show] = relationship(back_populates="props_list")
    prop_type: Mapped[PropType] = relationship(back_populates="prop_items")
    scene_allocations: Mapped[list[PropsAllocation]] = relationship(
        back_populates="prop",
        cascade="all, delete-orphan",
    )
