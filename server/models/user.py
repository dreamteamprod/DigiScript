from sqlalchemy import Integer, Column, String, ForeignKey, Boolean

from models.models import db


class User(db.Model):
    __tablename__ = 'user'

    id = Column(Integer(), primary_key=True, autoincrement=True)
    username = Column(String(), index=True)
    password = Column(String())
    show_id = Column(Integer(), ForeignKey('shows.id'), index=True)
    is_admin = Column(Boolean())
