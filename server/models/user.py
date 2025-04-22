import datetime
import json
from functools import partial
from typing import Union

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from models.models import db
from registry.user_settings import UserSettingsRegistry


class User(db.Model):
    __tablename__ = "user"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    username = Column(String(), index=True)
    password = Column(String())
    is_admin = Column(Boolean())
    last_login = Column(DateTime())


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True)

    settings_type = Column(String, index=True)
    settings = Column(Text)

    created_at = Column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    updated_at = Column(
        DateTime,
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )

    @property
    def settings_dict(self):
        """Return settings as a Python dictionary"""
        return json.loads(self.settings) if self.settings else {}

    def update_settings(self, new_settings):
        """Update settings with validation"""
        # Validate the complete set of settings that would result from this update
        current = self.settings_dict
        merged = current.copy()
        merged.update(new_settings)

        errors = UserSettingsRegistry.validate(self.settings_type, merged)
        if errors:
            raise ValueError(f"Invalid settings: {', '.join(errors)}")

        # Apply the update
        self.settings = json.dumps(merged)
        self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    @classmethod
    def get_by_type(cls, user_id, settings_type: Union[db.Model, str], session):
        if issubclass(settings_type, db.Model):
            settings_type = settings_type.__tablename__
        if not UserSettingsRegistry.is_registered(settings_type):
            return []
        return (
            session.query(UserSettings)
            .filter_by(user_id=user_id)
            .filter_by(settings_type=settings_type)
            .all()
        )

    @classmethod
    def create_for_user(cls, user_id, settings_type, settings_data):
        """Create settings with validation"""
        errors = UserSettingsRegistry.validate(settings_type, settings_data)
        if errors:
            raise ValueError(f"Invalid settings: {', '.join(errors)}")

        settings = cls(
            user_id=user_id,
            settings_type=settings_type,
            settings=json.dumps(settings_data),
        )

        return settings

    @classmethod
    def get_default_settings(cls, settings_type):
        """Get default settings from registered model"""
        model_class = UserSettingsRegistry.registry()[settings_type]["model"]
        return model_class.to_settings_dict()
