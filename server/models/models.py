from sqlalchemy import Column, String, Float, Integer, Date, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship, backref

from utils.database import DigiSQLAlchemy

db = DigiSQLAlchemy()


class Session(db.Model):
    __tablename__ = 'sessions'

    internal_id = Column(String(255), primary_key=True)
    remote_ip = Column(String(255))
    last_ping = Column(Float())
    last_pong = Column(Float())
    is_editor = Column(Boolean(), default=False, index=True)


class Show(db.Model):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    start_date = Column(Date())
    end_date = Column(Date())
    created_at = Column(DateTime())
    edited_at = Column(DateTime())
    first_act_id = Column(Integer, ForeignKey('act.id'))

    # Relationships
    first_act = relationship('Act', uselist=False, foreign_keys=[first_act_id])

    cast_list = relationship("Cast")
    character_list = relationship('Character')
    character_group_list = relationship('CharacterGroup')
    act_list = relationship('Act', primaryjoin=lambda: Show.id == Act.show_id)
    scene_list = relationship('Scene')
    cue_type_list = relationship('CueType')


class Cast(db.Model):
    __tablename__ = 'cast'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    first_name = Column(String)
    last_name = Column(String)

    # Relationships
    character_list = relationship('Character', back_populates='cast_member')


character_group_association_table = Table(
    "character_group_association",
    db.Model.metadata,
    Column('character_group_id', ForeignKey('character_group.id'), primary_key=True),
    Column('character_id', ForeignKey('character.id'), primary_key=True)
)


class Character(db.Model):
    __tablename__ = 'character'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    played_by = Column(Integer, ForeignKey('cast.id'))
    name = Column(String)
    description = Column(String)

    cast_member = relationship("Cast", back_populates='character_list')
    character_groups = relationship('CharacterGroup', secondary=character_group_association_table,
                                    back_populates='characters')


class CharacterGroup(db.Model):
    __tablename__ = 'character_group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))

    name = Column(String)
    description = Column(String)

    characters = relationship('Character', secondary=character_group_association_table,
                              back_populates='character_groups')


class Act(db.Model):
    __tablename__ = 'act'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    name = Column(String)
    interval_after = Column(Boolean)
    first_scene_id = Column(Integer, ForeignKey('scene.id'))
    previous_act_id = Column(Integer, ForeignKey('act.id'))

    first_scene = relationship('Scene', uselist=False, foreign_keys=[first_scene_id])
    previous_act = relationship('Act', uselist=False, remote_side=[id],
                                backref=backref('next_act', uselist=False))


class Scene(db.Model):
    __tablename__ = 'scene'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    act_id = Column(Integer, ForeignKey('act.id'))
    name = Column(String)
    previous_scene_id = Column(Integer, ForeignKey('scene.id'))

    act = relationship('Act', uselist=False, backref=backref('scene_list'),
                       foreign_keys=[act_id])
    previous_scene = relationship('Scene', uselist=False, remote_side=[id],
                                  backref=backref('next_scene', uselist=False))


class CueType(db.Model):
    __tablename__ = 'cuetypes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))

    prefix = Column(String(5))
    description = Column(String(100))
    colour = Column(String())


class Script(db.Model):
    __tablename__ = 'script'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    current_revision = Column(Integer, ForeignKey('script_revisions.id'))

    revisions = relationship('ScriptRevision', uselist=True,
                             primaryjoin='ScriptRevision.script_id == Script.id')


class ScriptRevision(db.Model):
    __tablename__ = 'script_revisions'

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

    act = relationship('Act', uselist=False)
    scene = relationship('Scene', uselist=False)


class ScriptLineRevisionAssociation(db.Model):
    __tablename__ = 'script_line_revision_association'

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
                                                    viewonly=True))
    next_line: ScriptLine = relationship('ScriptLine', foreign_keys=[next_line_id])
    previous_line: ScriptLine = relationship('ScriptLine', foreign_keys=[previous_line_id])


class ScriptLinePart(db.Model):
    __tablename__ = 'script_line_parts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(Integer, ForeignKey('script_lines.id'))

    part_index = Column(Integer)
    character_id = Column(Integer, ForeignKey('character.id'))
    character_group_id = Column(Integer, ForeignKey('character_group.id'))
    line_text = Column(String)

    line = relationship('ScriptLine', uselist=False, foreign_keys=[line_id],
                        backref=backref('line_parts', uselist=True))
    character = relationship('Character', uselist=False)
    character_group = relationship('CharacterGroup', uselist=False)
