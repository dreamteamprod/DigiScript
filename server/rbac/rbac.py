from typing import Optional, Dict, TYPE_CHECKING

from models.models import db
from rbac.rbac_db import RBACDatabase
from rbac.role import Role

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class RBACController:

    def __init__(self, app: 'DigiScriptServer'):
        self.app = app
        self._rbac_db = RBACDatabase(app.get_db())

    def add_mapping(self, actor: type, resource: type) -> None:
        self._rbac_db.add_mapping(actor, resource)

    def give_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        self._rbac_db.give_role(actor, resource, role)

    def revoke_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        self._rbac_db.revoke_role(actor, resource, role)

    def get_roles(self, actor: db.Model) -> Optional[Dict]:
        return self._rbac_db.get_roles(actor)
