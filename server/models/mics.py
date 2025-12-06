from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import db


class Microphone(db.Model):
    __tablename__ = "microphones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"))

    name: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)

    allocations: Mapped[List["MicrophoneAllocation"]] = relationship(
        cascade="all, delete-orphan", back_populates="microphone"
    )


class MicrophoneAllocation(db.Model):
    __tablename__ = "microphone_allocations"

    mic_id: Mapped[int] = mapped_column(
        ForeignKey("microphones.id"), primary_key=True
    )
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene.id"), primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("character.id"), primary_key=True
    )

    microphone: Mapped["Microphone"] = relationship(
        back_populates="allocations"
    )
    scene: Mapped["Scene"] = relationship(
        back_populates="mic_allocations"
    )
    character: Mapped["Character"] = relationship(
        back_populates="mic_allocations"
    )
