"""ORM models for core entities."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(100), index=True)
    input_ref: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="started")
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200))
    transcript: Mapped[str] = mapped_column(Text)
    participants: Mapped[str | None] = mapped_column(Text, nullable=True)  # simple CSV for Phase 1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
