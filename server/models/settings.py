from sqlalchemy.orm import Mapped, mapped_column

from models.models import db


class SystemSettings(db.Model):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(nullable=False)
