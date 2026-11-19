"""SQLAlchemy models for the PCB inspector (SQLite)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _now() -> datetime:
    return datetime.now()


class Image(Base):
    """A stored board image: the reference or one of the test images."""

    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "reference" | "test"
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "reference" | "test"
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)

    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="image", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Image id={self.id} kind={self.kind} {self.width}x{self.height}>"


class Annotation(Base):
    """A named, user-drawn component rectangle on the reference board.

    Coordinates are normalized to [0, 1] so they survive any resize of the
    reference image (the detection pipeline maps them back to pixels).
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    image: Mapped[Image] = relationship("Image", back_populates="annotations")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Annotation id={self.id} name={self.name!r} x={self.x} y={self.y}>"


class Inspection(Base):
    """One inspection run: reference + up to 3 test images, with results JSON."""

    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_image_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    results_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Inspection id={self.id} status={self.status}>"


class TestImage(Base):
    """Join table: test images that belong to an inspection."""

    __tablename__ = "test_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    inspection_id: Mapped[int] = mapped_column(Integer, ForeignKey("inspections.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)


class Setting(Base):
    """User-tunable inspection thresholds (one row per key)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
