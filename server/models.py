from sqlalchemy import Column, String, Float, Integer, Date, DateTime
from tornado_sqlalchemy import SQLAlchemy

from utils.env_parser import EnvParser

env: EnvParser = EnvParser.instance()
db = SQLAlchemy(env.db_path)


class Session(db.Model):
    __tablename__ = 'sessions'

    remote_ip = Column(String(255), primary_key=True)
    last_ping = Column(Float())
    last_pong = Column(Float())


class Show(db.Model):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    start_date = Column(Date())
    end_date = Column(Date())
    created_at = Column(DateTime())
