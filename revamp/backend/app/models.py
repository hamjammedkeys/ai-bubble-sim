from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


def _uuid_pk() -> Mapped[str]:
    return mapped_column(String, primary_key=True, default=_uuid)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    filing_type: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    filed_date: Mapped[date | None] = mapped_column(Date)
    period: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[str] = _uuid_pk()
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list | None] = mapped_column(JSON, default=list)


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[str] = _uuid_pk()
    source_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    target_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    relationship_type: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str | None] = mapped_column(Text)
    evidence_class: Mapped[str] = mapped_column(Text, nullable=False)
    permitted_operation: Mapped[str | None] = mapped_column(Text)
    unsupported_operation: Mapped[str | None] = mapped_column(Text)
    passage_id: Mapped[str | None] = mapped_column(ForeignKey("passages.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="candidate")
    verification: Mapped[dict | None] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = _uuid_pk()
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    shock_json: Mapped[dict | None] = mapped_column(JSON)

    @property
    def origin_entity(self) -> str | None:
        """Expose the persisted shock origin without leaking the full engine payload."""
        value = (self.shock_json or {}).get("origin_entity")
        return value if isinstance(value, str) else None


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = _uuid_pk()
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"))
    results: Mapped[dict | None] = mapped_column(JSON)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
