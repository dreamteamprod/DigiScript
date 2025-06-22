from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from models.models import db


class Crew(db.Model):
    __tablename__ = "crew"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    first_name = Column(String)
    last_name = Column(String)


class SceneryAllocation(db.Model):
    __tablename__ = "scenery_allocation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenery_id = Column(Integer, ForeignKey("scenery.id", ondelete="CASCADE"))
    scene_id = Column(Integer, ForeignKey("scene.id", ondelete="CASCADE"))

    scenery = relationship(
        "Scenery",
        uselist=False,
        foreign_keys=[scenery_id],
        backref=backref("scene_allocations", uselist=True, cascade="all, delete"),
    )
    scene = relationship(
        "Scene",
        uselist=False,
        foreign_keys=[scene_id],
        backref=backref("scenery_allocations", uselist=True, cascade="all, delete"),
    )


class PropsAllocation(db.Model):
    __tablename__ = "props_allocation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    props_id = Column(Integer, ForeignKey("props.id", ondelete="CASCADE"))
    scene_id = Column(Integer, ForeignKey("scene.id", ondelete="CASCADE"))

    prop = relationship(
        "Props",
        uselist=False,
        foreign_keys=[props_id],
        backref=backref("scene_allocations", uselist=True, cascade="all, delete"),
    )
    scene = relationship(
        "Scene",
        uselist=False,
        foreign_keys=[scene_id],
        backref=backref("props_allocations", uselist=True, cascade="all, delete"),
    )


class Scenery(db.Model):
    __tablename__ = "scenery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    name = Column(String)
    description = Column(String)


class Props(db.Model):
    __tablename__ = "props"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    name = Column(String)
    description = Column(String)
