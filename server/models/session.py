from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from models.models import db


class Session(db.Model):
    __tablename__ = 'sessions'

    internal_id = Column(String(255), primary_key=True)
    remote_ip = Column(String(255))
    last_ping = Column(Float())
    last_pong = Column(Float())
    is_editor = Column(Boolean(), default=False, index=True)


class ShowSession(db.Model):
    __tablename__ = 'showsession'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    start_date_time = Column(DateTime())
    end_date_time = Column(DateTime())

    show = relationship('Show', uselist=False, foreign_keys=[show_id])
