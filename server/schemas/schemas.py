from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested

from models.cue import CueType, Cue
from models.script import ScriptRevision, ScriptLine, ScriptLinePart
from models.show import Show, Cast, Character, CharacterGroup, Act, Scene
from models.session import Session, ShowSession
from models.user import User


class SessionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Session
        load_instance = True


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True


class ShowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Show
        load_instance = True
        include_fk = True

    first_act_id = auto_field()


class CastSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Cast
        include_relationships = True
        load_instance = True

    character_list = Nested(lambda: CharacterSchema, many=True, exclude=('cast_member',))


class CharacterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Character
        include_relationships = True
        load_instance = True

    cast_member = Nested(CastSchema, many=False, exclude=('character_list',))


class CharacterGroupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CharacterGroup
        include_relationships = True
        load_instance = True


class ActSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Act
        include_relationships = True
        load_instance = True

    scene_list = Nested(lambda: SceneSchema, many=True, exclue=('act',))
    first_scene = Nested(lambda: SceneSchema, many=False, exclue=('act',))
    next_act = Nested(lambda: ActSchema(), many=False,
                      exclude=('previous_act', 'scene_list', 'first_scene'))
    previous_act = Nested(lambda: ActSchema(), many=False,
                          exclude=('next_act', 'scene_list', 'first_scene'))


class SceneSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Scene
        load_instance = True

    act = Nested(ActSchema, many=False, exclude=('scene_list', 'first_scene'))
    next_scene = Nested(lambda: SceneSchema(), many=False, exclude=('previous_scene',))
    previous_scene = Nested(lambda: SceneSchema(), many=False, exclude=('next_scene',))


class CueTypeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CueType
        load_instance = True


class CueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Cue
        load_instance = True
        include_fk = True


class ScriptRevisionsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptRevision
        load_instance = True

    previous_revision_id = auto_field()


class ScriptLineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptLine
        load_instance = True
        include_fk = True

    line_parts = Nested(lambda: ScriptLinePartSchema(), many=True)


class ScriptLinePartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptLinePart
        load_instance = True
        include_fk = True


class ShowSessionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ShowSession
        load_instance = True
