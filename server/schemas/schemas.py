from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested

from models.cue import Cue, CueType
from models.mics import Microphone, MicrophoneAllocation
from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptRevision,
    StageDirectionStyle,
)
from models.session import Interval, Session, ShowSession
from models.show import Act, Cast, Character, CharacterGroup, Scene, Show
from models.user import User, UserSettings
from registry.schema import get_registry


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
        exclude = ("password", "api_token")


@schema
class UserSettingsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = UserSettings
        load_instance = True
        include_fk = True
        exclude = ("_user_id", "_created_at", "_updated_at")


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
class IntervalSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Interval
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
