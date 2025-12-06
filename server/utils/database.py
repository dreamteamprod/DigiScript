import functools
from contextlib import asynccontextmanager, contextmanager
from typing import Callable, List

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from tornado.ioloop import IOLoop


class DeleteMixin:
    def pre_delete(self, session: "DigiDBSession"):
        raise NotImplementedError

    def post_delete(self, session: "DigiDBSession"):
        raise NotImplementedError


class DigiDBSession(Session):
    """Custom session class with delete hook support."""

    def __init__(self, db=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def _delete_impl(self, state, obj, head):
        """Override delete to call hooks before and after deletion."""
        # Call registered delete hooks
        for hook in self.db.delete_hooks:
            hook(self, obj)

        # Call DeleteMixin methods if object implements them
        if isinstance(obj, DeleteMixin):
            obj.pre_delete(self)
            super()._delete_impl(state, obj, head)
            obj.post_delete(self)
        else:
            super()._delete_impl(state, obj, head)


class DigiSQLAlchemy:
    """Custom SQLAlchemy wrapper replacing tornado-sqlalchemy."""

    def __init__(self, url=None, binds=None, session_options=None, engine_options=None):
        self._engine = None
        self._sessionmaker = None
        self._delete_hooks: List[Callable] = []
        self.Model = None

        # Create declarative base
        self.Model = self.make_declarative_base()

        # Configure if URL provided
        if url:
            self.configure(url, binds, session_options, engine_options)

    def configure(
        self, url=None, binds=None, session_options=None, engine_options=None
    ):
        """Configure the database engine and session factory."""
        # Create engine
        engine_opts = engine_options or {}
        self._engine = create_engine(url, **engine_opts)

        # Add SQLite foreign key support if using SQLite
        if "sqlite" in str(self._engine.url):

            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Create session factory
        session_opts = session_options or {}
        # Set expire_on_commit=False by default for SQLAlchemy 2.0 compatibility
        # This allows objects to be used after session commit/close without triggering detached instance errors
        if "expire_on_commit" not in session_opts:
            session_opts["expire_on_commit"] = False
        self._sessionmaker = sessionmaker(
            bind=self._engine, class_=DigiDBSession, db=self, **session_opts
        )

        # For backward compatibility - expose sessionmaker as attribute
        # This allows existing code like `db.sessionmaker()` to work
        self.sessionmaker = self._create_session_context

    def _create_session_context(self):
        """Create a session context manager.

        This method is assigned to self.sessionmaker for backward compatibility.
        """
        return self._session_context_manager()

    @contextmanager
    def _session_context_manager(self):
        """Synchronous context manager for sessions."""
        session = self._sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def async_session(self):
        """Async context manager for sessions (for future async support)."""

        def _make_session():
            return self._sessionmaker()

        def _commit(session):
            session.commit()

        def _rollback(session):
            session.rollback()

        def _close(session):
            session.close()

        # Run session operations in executor to avoid blocking event loop
        session = await IOLoop.current().run_in_executor(None, _make_session)
        try:
            yield session
            await IOLoop.current().run_in_executor(None, _commit, session)
        except Exception:
            await IOLoop.current().run_in_executor(None, _rollback, session)
            raise
        finally:
            await IOLoop.current().run_in_executor(None, _close, session)

    @functools.lru_cache
    def get_mapper_for_table(self, tablename):
        """Get the mapped entity for a table name."""
        for mapper in self.Model.registry.mappers:
            if mapper.mapped_table.fullname == tablename:
                return mapper.entity
        return None

    def make_declarative_base(self):
        """Create declarative base with naming conventions."""
        convention = {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
        metadata = MetaData(naming_convention=convention)
        Base = declarative_base(metadata=metadata)

        # Allow legacy type annotations without Mapped[] for SQLAlchemy 2.0 compatibility
        # This enables gradual migration of type annotations
        Base.__allow_unmapped__ = True

        return Base

    @property
    def delete_hooks(self):
        """Get list of registered delete hooks."""
        return self._delete_hooks

    def register_delete_hook(self, hook: Callable):
        """Register a delete hook to be called when objects are deleted."""
        if hook not in self._delete_hooks:
            self._delete_hooks.append(hook)

    @property
    def metadata(self):
        """Get metadata from the declarative base."""
        return self.Model.metadata

    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine

    def create_all(self):
        """Create all tables in the database."""
        self.metadata.create_all(self._engine)

    def drop_all(self):
        """Drop all tables from the database."""
        self.metadata.drop_all(self._engine)
