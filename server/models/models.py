import datetime
import json
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, inspect, ForeignKey
from sqlalchemy.orm import relationship
from tornado_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def to_json(model: db.Model) -> dict:
    ret = {}
    for col in inspect(model).mapper.column_attrs:
        key = col.key
        val = getattr(model, col.key)

        if isinstance(val, (datetime.date, datetime.datetime)):
            val = val.isoformat()

        # Go to and from json here to make sure it is serializable
        ret[key] = json.loads(json.dumps(val))

    return ret


class Session(db.Model):
    __tablename__ = 'sessions'

    internal_id = Column(String(255), primary_key=True)
    remote_ip = Column(String(255))
    last_ping = Column(Float())
    last_pong = Column(Float())


class Show(db.Model):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    start_date = Column(Date())
    end_date = Column(Date())
    created_at = Column(DateTime())

    # Relationships
    cast_list = relationship("Cast")
    character_list = relationship('Character')


class Cast(db.Model):
    __tablename__ = 'cast'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    first_name = Column(String)
    last_name = Column(String)

    # Relationships
    character_list = relationship('Character', back_populates='cast_member')


class Character(db.Model):
    __tablename__ = 'character'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    played_by = Column(Integer, ForeignKey('cast.id'))
    name = Column(String)
    description = Column(String)

    cast_member = relationship("Cast", back_populates='character_list')
