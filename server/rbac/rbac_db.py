import functools
from collections import defaultdict
from copy import deepcopy
from typing import Optional, List, TYPE_CHECKING, Dict

from anytree import Node
from sqlalchemy import inspect, Column, ForeignKey, Integer, TypeDecorator, Table

from digi_server.logger import get_logger
from models.models import db
from models.show import Show
from rbac.exceptions import RBACException
from rbac.role import Role
from utils import tree
from utils.database import DigiSQLAlchemy

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


logger = get_logger()


class RoleCol(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if not isinstance(value, Role):
            raise Exception(f'RoleCol data type is incorrect. Got {type(value)} but should be Role')
        return value.value if value is not None else None

    def process_literal_param(self, value, dialect):
        if not isinstance(value, Role):
            raise Exception(f'RoleCol data type is incorrect. Got {type(value)} but should be Role')
        return value.value if value is not None else None

    @property
    def python_type(self):
        return Role

    def process_result_value(self, value, dialect):
        return Role(value)


def _get_mapping_columns(actor: db.Model, resource: db.Model) -> dict:
    actor_inspect = inspect(actor)
    resource_inspect = inspect(resource)
    cols = {}
    cols.update({
        f'{actor_inspect.mapper.mapped_table.fullname}_{col.key}': getattr(actor, col.key) for col in
        actor_inspect.mapper.primary_key
    })
    cols.update({
        f'{resource_inspect.mapper.mapped_table.fullname}_{col.key}': getattr(resource, col.key) for col in
        resource_inspect.mapper.primary_key
    })
    return cols


class RBACDatabase:

    def __init__(self, _db: DigiSQLAlchemy, app: 'DigiScriptServer'):
        self._db: DigiSQLAlchemy = _db
        self._app = app
        self._mappings = {}
        self._show_inspect = inspect(Show)
        self._resource_mappings = defaultdict(list)

    def add_mapping(self, actor: type, resource: type) -> None:
        if not isinstance(actor, type):
            raise RBACException('actor must be class object, not instance')
        if not isinstance(resource, type):
            raise RBACException('resource must be class object, not instance')

        actor_inspect = inspect(actor)
        resource_inspect = inspect(resource)

        if not self._has_link_to_show(actor_inspect.mapped_table):
            raise RBACException('actor class does not have a reference back to Show table')

        if not self._has_link_to_show(resource_inspect.mapped_table):
            raise RBACException('resource class does not have a reference back to Show table')

        table_name = f'rbac_{actor_inspect.mapped_table.fullname}_{resource_inspect.mapped_table.fullname}'
        if table_name in self._mappings:
            raise RBACException(f'RBAC mapping {table_name} already exists')

        actor_columns = {
            f'{actor_inspect.mapped_table.fullname}_{col.key}': Column(col.type, ForeignKey(
                f'{actor_inspect.mapped_table.fullname}.{col.key}'), primary_key=True) for col in
            actor_inspect.primary_key
        }
        resource_columns = {
            f'{resource_inspect.mapped_table.fullname}_{col.key}': Column(col.type, ForeignKey(
                f'{resource_inspect.mapped_table.fullname}.{col.key}'), primary_key=True) for col in
            resource_inspect.primary_key
        }

        attr_dict = {
            '__tablename__': table_name,
            'rbac_permissions': Column(RoleCol())
        }
        attr_dict.update(actor_columns)
        attr_dict.update(resource_columns)

        rbac_class = type(table_name, (db.Model,), attr_dict)
        self._mappings[table_name] = rbac_class
        self._resource_mappings[actor_inspect.mapped_table.fullname].append(resource)
        logger.info(f'Created RBAC mapping {table_name}')

    def _validate_mapping(self, actor: db.Model, resource: db.Model) -> str:
        if not isinstance(actor, db.Model):
            raise RBACException('actor must be class instance, not object')
        if not isinstance(resource, db.Model):
            raise RBACException('resource must be class instance, not object')

        actor_inspect = inspect(actor)
        resource_inspect = inspect(resource)
        table_name = (f'rbac_{actor_inspect.mapper.mapped_table.fullname}_'
                      f'{resource_inspect.mapper.mapped_table.fullname}')
        if table_name not in self._mappings:
            raise RBACException('Mapping for actor and resource not created')

        return table_name

    def give_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        table_name = self._validate_mapping(actor, resource)
        cols = _get_mapping_columns(actor, resource)

        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if rbac_assignment:
                rbac_assignment.rbac_permissions |= role
            else:
                rbac_assignment = self._mappings[table_name](**cols)
                rbac_assignment.rbac_permissions = role
                session.add(rbac_assignment)
            session.commit()

    def revoke_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        table_name = self._validate_mapping(actor, resource)
        cols = _get_mapping_columns(actor, resource)

        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if not rbac_assignment:
                raise RBACException('actor does not have any roles assigned for the resource')
            rbac_assignment.rbac_permissions &= ~role
            session.commit()

    def has_role(self, actor: db.Model, resource: db.Model, role: Role) -> bool:
        table_name = self._validate_mapping(actor, resource)
        cols = _get_mapping_columns(actor, resource)
        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if not rbac_assignment:
                return False
            return role in rbac_assignment.rbac_permissions

    def get_roles(self, actor: db.Model, resource: db.Model) -> Role:
        table_name = self._validate_mapping(actor, resource)
        cols = _get_mapping_columns(actor, resource)
        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if not rbac_assignment:
                return Role(0)
            return rbac_assignment.rbac_permissions

    def get_all_roles(self, actor: db.Model) -> Dict:
        roles = defaultdict(list)
        resources = self.get_resources_for_actor(actor.__class__)
        for resource in resources:
            resource_inspect = inspect(resource)
            for rbac_object in self.get_objects_for_resource(resource):
                roles[resource_inspect.mapped_table.fullname].append([rbac_object, self.get_roles(actor, rbac_object)])
        return roles

    @functools.lru_cache()
    def _has_link_to_show(self, table: Table):
        return self.__has_link_to_show(table)

    def __has_link_to_show(self, table: Table, checked_tables=None):
        if checked_tables is None:
            checked_tables = []
        if table.fullname == self._show_inspect.mapped_table.fullname:
            return True
        if table.foreign_key_constraints and table.fullname not in checked_tables:
            checked_tables.append(table.fullname)
            return any(self.__has_link_to_show(fkc.referred_table, checked_tables)
                       for fkc in table.foreign_key_constraints)
        return False

    @functools.lru_cache()
    def _get_link_to_show(self, table: Table):
        if not self._has_link_to_show(table):
            return None

        root = Node(table.fullname, table=table)
        self.__get_link_to_show(table, root)
        return tree.flatten(root, attr='table')

    def __get_link_to_show(self, table: Table, root: Node, checked_tables=None):
        if checked_tables is None:
            checked_tables = []
        if table.fullname == self._show_inspect.mapped_table.fullname:
            if table.fullname in checked_tables:
                checked_tables.remove(table.fullname)
            return
        if table.foreign_key_constraints:
            for fkc in table.foreign_key_constraints:
                if fkc.referred_table.fullname in checked_tables:
                    continue
                checked_tables.append(fkc.referred_table.fullname)
                if fkc.referred_table.fullname == table.fullname:
                    continue
                if self._has_link_to_show(fkc.referred_table):
                    self.__get_link_to_show(
                        fkc.referred_table,
                        Node(fkc.referred_table.fullname, table=fkc.referred_table, parent=root),
                        checked_tables
                    )

    def get_resources_for_actor(self, actor: db.Model) -> Optional[List[db.Model]]:
        if not isinstance(actor, type):
            raise RBACException('actor must be class object, not instance')
        actor_inspect = inspect(actor)
        if actor_inspect.mapped_table.fullname in self._resource_mappings:
            return self._resource_mappings[actor_inspect.mapped_table.fullname]
        return None

    def get_objects_for_resource(self, resource: db.Model) -> Optional[List[db.Model]]:
        if not isinstance(resource, type):
            raise RBACException('resource must be class object, not instance')

        current_show = self._app.digi_settings.settings.get('current_show').get_value()
        if not current_show:
            return []

        resource_inspect = inspect(resource)
        show_paths = self._get_link_to_show(resource_inspect.mapped_table)
        if show_paths is None:
            return []

        final_results = set()
        with self._db.sessionmaker() as session:
            if not show_paths:
                previous_entities = [session.get(Show, current_show)]
                return previous_entities

            for _show_path in show_paths:
                show_path = deepcopy(_show_path)
                show_path.reverse()
                previous_entities = [session.get(Show, current_show)]
                if not show_path:
                    return previous_entities
                valid = True
                for table in show_path[1:]:
                    if not previous_entities:
                        valid = False
                        break
                    results = []
                    for prev_entity in previous_entities:
                        previous_inspect = inspect(prev_entity)
                        cols = {}
                        for foreign_key in table.foreign_keys:
                            fk_table = foreign_key.constraint.referred_table
                            if fk_table.fullname == previous_inspect.mapper.mapped_table.fullname:
                                cols[foreign_key.parent.key] = getattr(prev_entity, foreign_key.column.key)
                        if cols:
                            results.extend(session.query(
                                self._db.get_mapper_for_table(table.fullname)).
                                           filter_by(**cols).all())
                    previous_entities = results
                if valid:
                    final_results.update(previous_entities)
            return list(final_results)
