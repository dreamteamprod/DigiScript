import functools
import os.path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker
from tornado_sqlalchemy import SQLAlchemy, SessionEx

from digi_server.logger import get_logger


class DeleteMixin:
    def pre_delete(self, session: 'DigiDBSession'):
        raise NotImplementedError

    def post_delete(self, session: 'DigiDBSession'):
        raise NotImplementedError


class DigiDBSession(SessionEx):

    def _delete_impl(self, state, obj, head):
        if isinstance(obj, DeleteMixin):
            obj.pre_delete(self)
            super()._delete_impl(state, obj, head)
            obj.post_delete(self)
        else:
            super()._delete_impl(state, obj, head)


class DigiSQLAlchemy(SQLAlchemy):

    def __init__(self, url=None, binds=None, session_options=None, engine_options=None):
        self.sessionmaker = None
        super().__init__(url, binds, session_options, engine_options)

    def configure(self, url=None, binds=None, session_options=None, engine_options=None):
        super().configure(url, binds, session_options, engine_options)
        self.sessionmaker = sessionmaker(class_=DigiDBSession, db=self, **(session_options or {}))

    @functools.lru_cache
    def get_mapper_for_table(self, tablename):
        for mapper in self.Model.registry.mappers:
            if mapper.mapped_table.fullname == tablename:
                return mapper.entity
        return None

    def get_alembic_config(self, settings_path):
        alembic_cfg_path = os.path.join(os.path.dirname(__file__), '..', 'alembic.ini')
        alembic_cfg = Config(alembic_cfg_path)
        # Override config options with specific ones based on this running instance
        alembic_cfg.set_main_option('digiscript.config', settings_path)
        alembic_cfg.set_main_option('configure_logging', 'False')
        return alembic_cfg

    def run_migrations(self, settings_path):
        get_logger().info('Running database migrations via Alembic')
        # Run the upgrade on the database
        command.upgrade(self.get_alembic_config(settings_path), 'head')

    def check_migrations(self, settings_path):
        get_logger().info('Checking database migrations via Alembic')
        # Run the upgrade on the database
        command.check(self.get_alembic_config(settings_path))
