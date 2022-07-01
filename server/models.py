from sqlalchemy import Column, String, Float
from tornado_sqlalchemy import SQLAlchemy

from env_parser import EnvParser

env: EnvParser = EnvParser.instance()
db = SQLAlchemy(env.db_path)


class Session(db.Model):
    __tablename__ = 'sessions'

    remote_ip = Column(String(255), primary_key=True)
    last_ping = Column(Float())
    last_pong = Column(Float())
