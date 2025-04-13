from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from models.models import db


class User(db.Model):
    __tablename__ = "user"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    username = Column(String(), index=True)
    password = Column(String())
    show_id = Column(Integer(), ForeignKey("shows.id"), index=True)
    is_admin = Column(Boolean())
    last_login = Column(DateTime())
