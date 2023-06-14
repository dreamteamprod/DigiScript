from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean
from sqlalchemy.orm import relationship, backref

from models.models import db
from utils.database import DeleteMixin


class Script(db.Model):
    __tablename__ = 'script'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    current_revision = Column(Integer, ForeignKey('script_revisions.id'))

    revisions = relationship('ScriptRevision', uselist=True,
                             primaryjoin='ScriptRevision.script_id == Script.id')


class ScriptRevision(db.Model):
    __tablename__ = 'script_revisions'
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey('script.id'))

    revision = Column(Integer)
    created_at = Column(DateTime)
    edited_at = Column(DateTime)
    description = Column(String)
    previous_revision_id = Column(Integer, ForeignKey('script_revisions.id', ondelete='SET NULL'))

    previous_revision = relationship('ScriptRevision', foreign_keys=[previous_revision_id])


class ScriptLine(db.Model):
    __tablename__ = 'script_lines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    act_id = Column(Integer, ForeignKey('act.id'))
    scene_id = Column(Integer, ForeignKey('scene.id'))
    page = Column(Integer, index=True)
    stage_direction = Column(Boolean)

    act = relationship('Act', uselist=False, back_populates='lines')
    scene = relationship('Scene', uselist=False, back_populates='lines')


class ScriptLineRevisionAssociation(db.Model, DeleteMixin):
    __tablename__ = 'script_line_revision_association'
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

    revision_id = Column(Integer, ForeignKey('script_revisions.id'), primary_key=True, index=True)
    line_id = Column(Integer, ForeignKey('script_lines.id'), primary_key=True, index=True)

    next_line_id = Column(Integer, ForeignKey('script_lines.id'))
    previous_line_id = Column(Integer, ForeignKey('script_lines.id'))

    revision: ScriptRevision = relationship('ScriptRevision',
                                            foreign_keys=[revision_id],
                                            uselist=False,
                                            backref=backref('line_associations',
                                                            uselist=True,
                                                            cascade='all, delete'))
    line: ScriptLine = relationship('ScriptLine',
                                    foreign_keys=[line_id],
                                    uselist=False,
                                    backref=backref('revision_associations',
                                                    uselist=True,
                                                    cascade='all, delete'))
    next_line: ScriptLine = relationship('ScriptLine', foreign_keys=[next_line_id])
    previous_line: ScriptLine = relationship('ScriptLine', foreign_keys=[previous_line_id])

    def pre_delete(self, session):
        if self.line and len(self.line.revision_associations) == 1:
            session.delete(self.line)

    def post_delete(self, session):
        pass


class ScriptLinePart(db.Model):
    __tablename__ = 'script_line_parts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(Integer, ForeignKey('script_lines.id'))

    part_index = Column(Integer)
    character_id = Column(Integer, ForeignKey('character.id'))
    character_group_id = Column(Integer, ForeignKey('character_group.id'))
    line_text = Column(String)

    line = relationship('ScriptLine', uselist=False, foreign_keys=[line_id],
                        backref=backref('line_parts', uselist=True,
                                        cascade='all, delete-orphan'))
    character = relationship('Character', uselist=False)
    character_group = relationship('CharacterGroup', uselist=False)


class ScriptCuts(db.Model):
    __tablename__ = 'script_line_cuts'

    line_part_id = Column(Integer, ForeignKey('script_line_parts.id'), primary_key=True, index=True)
    revision_id = Column(Integer, ForeignKey('script_revisions.id'), primary_key=True, index=True)

    line_part = relationship('ScriptLinePart', uselist=False, foreign_keys=[line_part_id],
                             backref=backref('line_part_cuts', uselist=False,
                                             cascade='all, delete-orphan'))
    revision = relationship('ScriptRevision', uselist=False, foreign_keys=[revision_id],
                            backref=backref('line_part_cuts', uselist=True,
                                            cascade='all, delete-orphan'))
