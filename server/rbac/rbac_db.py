from typing import Optional, Dict

from sqlalchemy import inspect, Column, ForeignKey, Integer, TypeDecorator

from digi_server.logger import get_logger
from models.models import db
from rbac.role import Role
from utils.database import DigiSQLAlchemy


logger = get_logger()


class RBACException(Exception):
    pass


class RoleCol(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if not isinstance(value, Role):
            raise Exception(f'RoleCol data type is incorrect. Got {type(value)} but should be Role')
        return value.value

    def process_result_value(self, value, dialect):
        return Role(value)


class RBACDatabase:

    def __init__(self, _db: DigiSQLAlchemy):
        self._db: DigiSQLAlchemy = _db
        self._mappings = {}

    def add_mapping(self, actor: type, resource: type) -> None:
        if not isinstance(actor, type):
            raise RBACException('actor must be class object, not instance')
        if not isinstance(resource, type):
            raise RBACException('resource must be class object, not instance')

        actor_inspect = inspect(actor)
        resource_inspect = inspect(resource)
        table_name = f'rbac_{actor_inspect.mapped_table.fullname}_{resource_inspect.mapped_table.fullname}'

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

    def _get_mapping_columns(self, actor: db.Model, resource: db.Model) -> dict:
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

    def give_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        table_name = self._validate_mapping(actor, resource)
        cols = self._get_mapping_columns(actor, resource)

        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if rbac_assignment:
                rbac_assignment.rbac_permissions |= role
            else:
                rbac_assignment = self._mappings[table_name](**cols)
                rbac_assignment.rbac_permissions |= role
                session.add(rbac_assignment)
            session.commit()

    def revoke_role(self, actor: db.Model, resource: db.Model, role: Role) -> None:
        table_name = self._validate_mapping(actor, resource)
        cols = self._get_mapping_columns(actor, resource)

        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if not rbac_assignment:
                raise RBACException('actor does not have any roles assigned for the resource')
            rbac_assignment.rbac_permissions &= ~role
            session.commit()

    def has_role(self, actor: db.Model, resource: db.Model, role: Role):
        table_name = self._validate_mapping(actor, resource)
        cols = self._get_mapping_columns(actor, resource)
        with self._db.sessionmaker() as session:
            rbac_assignment = session.query(self._mappings[table_name]).get(cols)
            if not rbac_assignment:
                return False
            return role in rbac_assignment.rbac_permissions

    def get_roles(self, actor: db.Model) -> Optional[Dict]:
        if not isinstance(actor, db.Model):
            raise RBACException('actor must be class instance, not object')
        return None
