from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db
from models.show import Scene, Show


class Crew(db.Model):
    __tablename__ = "crew"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    first_name: Mapped[str | None] = mapped_column()
    last_name: Mapped[str | None] = mapped_column()

    show: Mapped["Show"] = relationship(back_populates="crew_list")


class SceneryAllocation(db.Model):
    __tablename__ = "scenery_allocation"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenery_id: Mapped[int] = mapped_column(
        ForeignKey("scenery.id", ondelete="CASCADE")
    )
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"))

    scenery: Mapped["Scenery"] = relationship(
        back_populates="scene_allocations",
        foreign_keys=[scenery_id],
    )
    scene: Mapped["Scene"] = relationship(
        back_populates="scenery_allocations",
        foreign_keys=[scene_id],
    )


class PropsAllocation(db.Model):
    __tablename__ = "props_allocation"

    id: Mapped[int] = mapped_column(primary_key=True)
    props_id: Mapped[int] = mapped_column(ForeignKey("props.id", ondelete="CASCADE"))
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"))

    prop: Mapped["Props"] = relationship(
        back_populates="scene_allocations",
        foreign_keys=[props_id],
    )
    scene: Mapped["Scene"] = relationship(
        back_populates="props_allocations",
        foreign_keys=[scene_id],
    )


class Scenery(db.Model):
    __tablename__ = "scenery"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    name: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped["Show"] = relationship(back_populates="scenery_list")
    scene_allocations: Mapped[list["SceneryAllocation"]] = relationship(
        back_populates="scenery",
        cascade="all, delete-orphan",
    )


class Props(db.Model):
    __tablename__ = "props"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    name: Mapped[str | None] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    show: Mapped["Show"] = relationship(back_populates="props_list")
    scene_allocations: Mapped[list["PropsAllocation"]] = relationship(
        back_populates="prop",
        cascade="all, delete-orphan",
    )
