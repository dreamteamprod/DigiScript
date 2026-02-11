from __future__ import annotations

from typing import List

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
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
    crew_assignments: Mapped[List["CrewAssignment"]] = relationship(
        back_populates="crew",
        cascade="all, delete-orphan",
    )


class CrewAssignment(db.Model):
    """
    Assigns a crew member to SET or STRIKE an item (prop or scenery) in a specific scene.

    The scene must be a block boundary for the item:
    - SET assignments go on the first scene of a block
    - STRIKE assignments go on the last scene of a block

    Exactly one of prop_id or scenery_id must be set (enforced by CHECK constraint).
    """

    __tablename__ = "crew_assignment"
    __table_args__ = (
        # Exactly one of prop_id or scenery_id must be set
        CheckConstraint(
            "(prop_id IS NOT NULL AND scenery_id IS NULL) OR "
            "(prop_id IS NULL AND scenery_id IS NOT NULL)",
            name="exactly_one_item_type",
        ),
        # Prevent duplicate assignments for props
        UniqueConstraint(
            "crew_id",
            "scene_id",
            "assignment_type",
            "prop_id",
            name="uq_crew_prop_assignment",
        ),
        # Prevent duplicate assignments for scenery
        UniqueConstraint(
            "crew_id",
            "scene_id",
            "assignment_type",
            "scenery_id",
            name="uq_crew_scenery_assignment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crew.id", ondelete="CASCADE"))
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"))
    assignment_type: Mapped[str] = mapped_column()  # 'set' or 'strike'

    # Two nullable FKs - exactly one must be non-null
    prop_id: Mapped[int | None] = mapped_column(
        ForeignKey("props.id", ondelete="CASCADE")
    )
    scenery_id: Mapped[int | None] = mapped_column(
        ForeignKey("scenery.id", ondelete="CASCADE")
    )

    # Relationships
    crew: Mapped["Crew"] = relationship(back_populates="crew_assignments")
    scene: Mapped[Scene] = relationship(back_populates="crew_assignments")
    prop: Mapped["Props | None"] = relationship(back_populates="crew_assignments")
    scenery: Mapped["Scenery | None"] = relationship(back_populates="crew_assignments")


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
    crew_assignments: Mapped[List["CrewAssignment"]] = relationship(
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
    crew_assignments: Mapped[List["CrewAssignment"]] = relationship(
        back_populates="prop",
        cascade="all, delete-orphan",
    )
