import datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from models.models import db


if TYPE_CHECKING:
    from models.show import Show
    from models.user import User


class Session(db.Model):
    __tablename__ = "sessions"

    internal_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    remote_ip: Mapped[str] = mapped_column(String(255))
    last_ping: Mapped[float] = mapped_column()
    last_pong: Mapped[float] = mapped_column()
    is_editor: Mapped[bool] = mapped_column(default=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), index=True
    )

    user: Mapped["User"] = relationship(
        uselist=False, backref=backref("sessions", uselist=True)
    )


class ShowSession(db.Model):
    __tablename__ = "showsession"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    start_date_time: Mapped[datetime.datetime] = mapped_column()
    end_date_time: Mapped[datetime.datetime] = mapped_column()

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), index=True
    )
    client_internal_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("sessions.internal_id", ondelete="SET NULL")
    )
    last_client_internal_id: Mapped[str | None] = mapped_column(String(255))
    latest_line_ref: Mapped[str | None] = mapped_column()
    current_interval_id: Mapped[int | None] = mapped_column(
        ForeignKey("showinterval.id", ondelete="SET NULL")
    )

    show: Mapped["Show"] = relationship(uselist=False, foreign_keys=[show_id])
    user: Mapped["User"] = relationship(uselist=False, foreign_keys=[user_id])
    client: Mapped["Session"] = relationship(
        uselist=False,
        foreign_keys=[client_internal_id],
        backref=backref("live_session", uselist=False),
    )


class Interval(db.Model):
    __tablename__ = "showinterval"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("showsession.id", ondelete="CASCADE")
    )
    act_id: Mapped[int] = mapped_column(ForeignKey("act.id", ondelete="CASCADE"))
    start_datetime: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    end_datetime: Mapped[datetime.datetime | None] = mapped_column(default=None)
    initial_length: Mapped[float] = mapped_column(default=0)
