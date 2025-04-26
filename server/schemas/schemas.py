from typing import Optional

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field
from marshmallow_sqlalchemy.fields import Nested

from models.cue import Cue, CueType
from models.mics import Microphone, MicrophoneAllocation
from models.models import db
from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptRevision,
    StageDirectionStyle,
)
from models.session import Session, ShowSession
from models.show import Act, Cast, Character, CharacterGroup, Scene, Show
from models.user import User


class SchemaRegistry:
    def __init__(self):
        self._forward_registry = {}
        self._backward_registry = {}

    def set(self, key, value):
        self._forward_registry[key] = value
        self._backward_registry[value] = key

    def get_schema_by_model(self, key) -> Optional[SQLAlchemySchema]:
        return self._backward_registry.get(key, None)

    def get_model_by_schema(self, key) -> db.Model:
        return self._forward_registry.get(key, None)


registry = SchemaRegistry()


def get_registry():
    return registry


def schema(cls):
    meta_cls = getattr(cls, "Meta", None)
    if hasattr(meta_cls, "model"):
        get_registry().set(cls, meta_cls.model)
    return cls


@schema
class SessionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Session
        load_instance = True


@schema
class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True
        exclude = ("password",)


@schema
class ShowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Show
        load_instance = True
        include_fk = True

    first_act_id = auto_field()


@schema
class CastSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Cast
        include_relationships = True
        load_instance = True

    character_list = Nested(
        lambda: CharacterSchema, many=True, exclude=("cast_member",)
    )


@schema
class CharacterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Character
        include_relationships = True
        load_instance = True

    cast_member = Nested(CastSchema, many=False, exclude=("character_list",))


@schema
class CharacterGroupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CharacterGroup
        include_relationships = True
        load_instance = True


@schema
class ActSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Act
        include_relationships = True
        load_instance = True


@schema
class SceneSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Scene
        include_relationships = True
        load_instance = True


@schema
class CueTypeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CueType
        load_instance = True


@schema
class CueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Cue
        load_instance = True
        include_fk = True


@schema
class ScriptSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Script
        load_instance = True


@schema
class ScriptRevisionsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptRevision
        load_instance = True

    previous_revision_id = auto_field()


@schema
class ScriptLineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptLine
        load_instance = True
        include_fk = True

    line_parts = Nested(
        lambda: ScriptLinePartSchema(), many=True  # pylint:disable=unnecessary-lambda
    )


@schema
class ScriptLinePartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptLinePart
        load_instance = True
        include_fk = True


@schema
class ScriptCutsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ScriptCuts
        load_instance = True
        include_fk = True


@schema
class StageDirectionStyleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = StageDirectionStyle
        load_instance = True
        include_fk = True


@schema
class ShowSessionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ShowSession
        load_instance = True
        include_fk = True


@schema
class MicrophoneSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Microphone
        load_instance = True
        include_fk = True


@schema
class MicrophoneAllocationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = MicrophoneAllocation
        load_instance = True
        include_fk = True
