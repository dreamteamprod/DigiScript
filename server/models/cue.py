from sqlalchemy import Column, Integer, ForeignKey, String

from models.models import db


class CueType(db.Model):
    __tablename__ = 'cuetypes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))

    prefix = Column(String(5))
    description = Column(String(100))
    colour = Column(String())
