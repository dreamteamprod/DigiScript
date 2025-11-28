import datetime
import json
from functools import partial
from typing import Union

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from models.models import db
from registry.user_overrides import UserOverridesRegistry


class User(db.Model):
    __tablename__ = "user"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    username = Column(String(), index=True)
    password = Column(String())
    is_admin = Column(Boolean())
    last_login = Column(DateTime())
    last_seen = Column(DateTime())
    api_token = Column(String(), nullable=True, index=True)


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    # User editable settings
    enable_script_auto_save = Column(Boolean, default=True)
    script_auto_save_interval = Column(Integer, default=10)
    cue_position_right = Column(Boolean, default=False)

    # Hidden Properties (None user editable, marked with _)
    # Make sure to also mark these as hidden in the Schema for this in schemas/schemas.py
    _user_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    _created_at = Column(
        DateTime, default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    _updated_at = Column(
        DateTime,
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )


class UserOverrides(db.Model):
    __tablename__ = "user_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)

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

        errors = UserOverridesRegistry.validate(self.settings_type, merged)
        if errors:
            raise ValueError(f"Invalid settings: {', '.join(errors)}")

        # Apply the update
        self.settings = json.dumps(merged)
        self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    @classmethod
    def get_by_type(cls, user_id, settings_type: Union[db.Model, str], session):
        if issubclass(settings_type, db.Model):
            settings_type = settings_type.__tablename__
        if not UserOverridesRegistry.is_registered(settings_type):
            return []
        return (
            session.query(UserOverrides)
            .filter_by(user_id=user_id)
            .filter_by(settings_type=settings_type)
            .all()
        )

    @classmethod
    def create_for_user(cls, user_id, settings_type, settings_data):
        """Create settings with validation"""
        errors = UserOverridesRegistry.validate(settings_type, settings_data)
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
        model_class = UserOverridesRegistry.registry()[settings_type]["model"]
        return model_class.to_settings_dict()
