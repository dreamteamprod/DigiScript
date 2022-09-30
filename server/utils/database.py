from sqlalchemy.orm import sessionmaker
from tornado_sqlalchemy import SQLAlchemy, SessionEx


class DeleteMixin(object):
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
