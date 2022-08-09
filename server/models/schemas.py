from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested

from models.models import Show, Cast, Character


class ShowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Show
        include_relationships = True
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
