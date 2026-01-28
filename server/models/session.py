from __future__ import annotations

import datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db


if TYPE_CHECKING:
    from models.script import ScriptRevision
    from models.show import Show
    from models.user import User


class Session(db.Model):
    __tablename__ = "sessions"

    internal_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    remote_ip: Mapped[str | None] = mapped_column(String(255))
    last_ping: Mapped[float | None] = mapped_column()
    last_pong: Mapped[float | None] = mapped_column()
    is_editor: Mapped[bool | None] = mapped_column(default=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), index=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")
    live_session: Mapped[ShowSession] = relationship(
        foreign_keys="[ShowSession.client_internal_id]",
        back_populates="client",
    )


session_tag_association_table = Table(
    "session_tag_associations",
    db.Model.metadata,
    Column(
        "session_id", ForeignKey("showsession.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "tag_id", ForeignKey("session_tags.id", ondelete="CASCADE"), primary_key=True
    ),
)


class ShowSession(db.Model):
    __tablename__ = "showsession"

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))
    script_revision_id: Mapped[int] = mapped_column(ForeignKey("script_revisions.id"))
    start_date_time: Mapped[datetime.datetime | None] = mapped_column()
    end_date_time: Mapped[datetime.datetime | None] = mapped_column()

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

    show: Mapped[Show] = relationship(uselist=False, foreign_keys=[show_id])
    revision: Mapped[ScriptRevision] = relationship(
        uselist=False, foreign_keys=[script_revision_id]
    )
    user: Mapped[User] = relationship(uselist=False, foreign_keys=[user_id])
    client: Mapped[Session] = relationship(
        foreign_keys=[client_internal_id],
        back_populates="live_session",
    )
    tags: Mapped[list[SessionTag]] = relationship(
        secondary=session_tag_association_table, back_populates="sessions"
    )


class Interval(db.Model):
    __tablename__ = "showinterval"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("showsession.id", ondelete="CASCADE")
    )
    act_id: Mapped[int | None] = mapped_column(ForeignKey("act.id", ondelete="CASCADE"))
    start_datetime: Mapped[datetime.datetime | None] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    end_datetime: Mapped[datetime.datetime | None] = mapped_column(default=None)
    initial_length: Mapped[float | None] = mapped_column(default=0)


class SessionTag(db.Model):
    __tablename__ = "session_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int | None] = mapped_column(
        ForeignKey("shows.id", ondelete="CASCADE")
    )
    tag: Mapped[str] = mapped_column(String(255))
    colour: Mapped[str] = mapped_column(String(16))

    show: Mapped[Show] = relationship(uselist=False, foreign_keys=[show_id])
    sessions: Mapped[list[ShowSession]] = relationship(
        secondary=session_tag_association_table, back_populates="tags"
    )
