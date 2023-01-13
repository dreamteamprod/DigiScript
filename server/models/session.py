from sqlalchemy import Column, String, Float, Boolean

from models.models import db


class Session(db.Model):
    __tablename__ = 'sessions'

    internal_id = Column(String(255), primary_key=True)
    remote_ip = Column(String(255))
    last_ping = Column(Float())
    last_pong = Column(Float())
    is_editor = Column(Boolean(), default=False, index=True)
