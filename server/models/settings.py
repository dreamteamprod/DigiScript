from sqlalchemy import Column, String

from models.models import db


class SystemSettings(db.Model):
    __tablename__ = "system_settings"
    
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
