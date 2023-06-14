from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref

from models.models import db


class Microphone(db.Model):
    __tablename__ = 'microphones'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))

    name = Column(String)
    description = Column(String)


class MicrophoneAllocation(db.Model):
    __tablename__ = 'microphone_allocations'

    mic_id = Column(Integer, ForeignKey('microphones.id'), primary_key=True)
    scene_id = Column(Integer, ForeignKey('scene.id'), primary_key=True)
    character_id = Column(Integer, ForeignKey('character.id'), primary_key=True)

    microphone = relationship('Microphone', uselist=False,
                              backref=backref('allocations', uselist=True,
                                              cascade='all, delete-orphan'))
    scene = relationship('Scene', uselist=False,
                         backref=backref('mic_allocations', uselist=True,
                                         cascade='all, delete-orphan'))
    character = relationship('Character', uselist=False,
                             backref=backref('mic_allocations', uselist=True,
                                             cascade='all, delete-orphan'))
