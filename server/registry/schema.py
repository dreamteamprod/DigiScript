from typing import TYPE_CHECKING, Optional

from marshmallow_sqlalchemy import SQLAlchemySchema


if TYPE_CHECKING:
    from models.models import db


class SchemaRegistry:
    def __init__(self):
        self._forward_registry = {}
        self._backward_registry = {}

    def set(self, key, value):
        self._forward_registry[key] = value
        self._backward_registry[value] = key

    def get_schema_by_model(self, key) -> Optional[SQLAlchemySchema]:
        return self._backward_registry.get(key, None)

    def get_model_by_schema(self, key) -> "db.Model":
        return self._forward_registry.get(key, None)


registry = SchemaRegistry()


def get_registry():
    return registry
