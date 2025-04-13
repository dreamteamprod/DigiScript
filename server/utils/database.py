import functools

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from tornado_sqlalchemy import BindMeta, SessionEx, SQLAlchemy


class DeleteMixin:
    def pre_delete(self, session: "DigiDBSession"):
        raise NotImplementedError

    def post_delete(self, session: "DigiDBSession"):
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

    def configure(
        self, url=None, binds=None, session_options=None, engine_options=None
    ):
        super().configure(url, binds, session_options, engine_options)
        self.sessionmaker = sessionmaker(
            class_=DigiDBSession, db=self, **(session_options or {})
        )

    @functools.lru_cache
    def get_mapper_for_table(self, tablename):
        for mapper in self.Model.registry.mappers:
            if mapper.mapped_table.fullname == tablename:
                return mapper.entity
        return None

    def make_declarative_base(self):
        convention = {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
        metadata = MetaData(naming_convention=convention)
        return declarative_base(metaclass=BindMeta, metadata=metadata)
