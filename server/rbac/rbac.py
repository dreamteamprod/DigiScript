from typing import TYPE_CHECKING, List, Optional

from models.models import db
from rbac.exceptions import RBACException
from rbac.rbac_db import RBACDatabase
from rbac.role import Role
from registry.schema import get_registry


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class RBACController:
    def __init__(self, app: "DigiScriptServer"):
        self.app = app
        self._rbac_db = RBACDatabase(app.get_db(), app)
        self._display_fields = {}

    @property
    def rbac_db(self):
        return self._rbac_db

    def add_mapping(
        self, actor: type, resource: type, display_fields: Optional[List] = None
    ) -> None:
        if display_fields is None:
            display_fields = []
        if not get_registry().get_schema_by_model(actor):
            raise RBACException("actor does not have a registered schema")
        if not get_registry().get_schema_by_model(resource):
            raise RBACException("resource does not have a registered schema")
        if len(display_fields) > 3:
            raise RBACException("Only 3 or fewer display fields are allowed")
        self._rbac_db.add_mapping(actor, resource)
        self._display_fields[resource] = [field.key for field in display_fields]

    def delete_actor(self, actor: db.Model) -> None:
        self._rbac_db.delete_actor(actor)

    def give_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        self._rbac_db.give_role(actor, resource, role)

    def revoke_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        self._rbac_db.revoke_role(actor, resource, role)

    def get_all_roles(self, actor: db.Model) -> List:
        return self._rbac_db.get_all_roles(actor)

    def get_roles(self, actor: db.Model, resource: db.Model) -> Role:
        return self._rbac_db.get_roles(actor, resource)

    def has_role(self, actor: db.Model, resource: db.Model, role: Role) -> bool:
        return self._rbac_db.has_role(actor, resource, role)

    def get_objects_for_resource(self, resource: db.Model) -> Optional[List[db.Model]]:
        return self._rbac_db.get_objects_for_resource(resource)

    def get_resources_for_actor(self, actor: db.Model) -> Optional[List[db.Model]]:
        return self._rbac_db.get_resources_for_actor(actor)

    def get_display_fields(self, resource: type):
        return self._display_fields.get(resource, [])
