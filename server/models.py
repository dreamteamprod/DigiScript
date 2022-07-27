import datetime
import json
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, inspect
from tornado_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def to_json(model: db.Model) -> dict:
    ret = {}
    for col in inspect(model).mapper.column_attrs:
        key = col.key
        val = getattr(model, col.key)

        if isinstance(val, (datetime.date, datetime.datetime)):
            val = val.isoformat()

        # Go to and from json here to make sure it is serializable
        ret[key] = json.loads(json.dumps(val))

    return ret


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
