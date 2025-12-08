import datetime
import json
from functools import partial
from typing import TYPE_CHECKING, List, Union

from sqlalchemy import ForeignKey, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db
from registry.user_overrides import UserOverridesRegistry


if TYPE_CHECKING:
    from models.session import Session


class User(db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(index=True)
    password: Mapped[str | None] = mapped_column()
    is_admin: Mapped[bool | None] = mapped_column()
    last_login: Mapped[datetime.datetime | None] = mapped_column()
    last_seen: Mapped[datetime.datetime | None] = mapped_column()
    api_token: Mapped[str | None] = mapped_column(index=True)

    sessions: Mapped[List["Session"]] = relationship(back_populates="user")


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    # User editable settings
    enable_script_auto_save: Mapped[bool | None] = mapped_column(default=True)
    script_auto_save_interval: Mapped[int | None] = mapped_column(default=10)
    cue_position_right: Mapped[bool | None] = mapped_column(default=False)

    # Hidden Properties (None user editable, marked with _)
    # Make sure to also mark these as hidden in the Schema for this in schemas/schemas.py
    _user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    _created_at: Mapped[datetime.datetime | None] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    _updated_at: Mapped[datetime.datetime | None] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )


class UserOverrides(db.Model):
    __tablename__ = "user_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )

    settings_type: Mapped[str | None] = mapped_column(index=True)
    settings: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime.datetime | None] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
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
        return session.scalars(
            select(UserOverrides)
            .where(UserOverrides.user_id == user_id)
            .where(UserOverrides.settings_type == settings_type)
        ).all()

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
