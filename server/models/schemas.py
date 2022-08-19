from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

from models.models import Show, Cast, Character, Session, Act, Scene


class SessionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Session
        load_instance = True


class ShowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Show
        load_instance = True


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
