import datetime
from functools import partial

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from models.models import db


class Session(db.Model):
    __tablename__ = "sessions"

    internal_id = Column(String(255), primary_key=True)
    remote_ip = Column(String(255))
    last_ping = Column(Float())
    last_pong = Column(Float())
    is_editor = Column(Boolean(), default=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), index=True)

    user = relationship(
        "User", uselist=False, backref=backref("sessions", uselist=True)
    )


class ShowSession(db.Model):
    __tablename__ = "showsession"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.id"))
    start_date_time = Column(DateTime())
    end_date_time = Column(DateTime())

    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), index=True)
    client_internal_id = Column(
        String(255), ForeignKey("sessions.internal_id", ondelete="SET NULL")
    )
    last_client_internal_id = Column(String(255))
    latest_line_ref = Column(String)
    current_interval_id = Column(
        Integer, ForeignKey("showinterval.id", ondelete="SET NULL")
    )

    show = relationship("Show", uselist=False, foreign_keys=[show_id])
    user = relationship("User", uselist=False, foreign_keys=[user_id])
    client = relationship(
        "Session",
        uselist=False,
        foreign_keys=[client_internal_id],
        backref=backref("live_session", uselist=False),
    )


class Interval(db.Model):
    __tablename__ = "showinterval"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("showsession.id", ondelete="CASCADE"))
    act_id = Column(Integer, ForeignKey("act.id", ondelete="CASCADE"))
    start_datetime = Column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    end_datetime = Column(DateTime, default=None)
    initial_length = Column(Float, default=0)
