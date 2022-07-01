from tornado_sqlalchemy import SQLAlchemy

from env_parser import EnvParser

env: EnvParser = EnvParser.instance()
db = SQLAlchemy(env.db_path)


class Session(db.Model):
    pass
