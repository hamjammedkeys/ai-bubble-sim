import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb

from fragility_map.extraction.candidates import RelationshipCandidateV2
from fragility_map.extraction.lifecycle import AuditEvent
from fragility_map.extraction.relationships import RelationshipCandidate
from fragility_map.extraction.verifier import VerificationResult
from fragility_map.ingestion.companies import CompanyConfig
from fragility_map.ingestion.official_pdfs import SourceRecord


class FragilityRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> duckdb.DuckDBPyConnection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.db_path))

    def create_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connect() as connection:
            connection.execute(schema_path.read_text(encoding="utf-8"))

    def upsert_companies(self, companies: Sequence[CompanyConfig]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO companies
                (company_id, ticker, name, sector_group, country)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(c.company_id, c.ticker, c.name, c.sector_group, c.country) for c in companies],
            )

    def list_companies(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT company_id, ticker, name, sector_group, country
                FROM companies
                ORDER BY rowid
                """
            ).fetchall()
        return [
            {
                "company_id": row[0],
                "ticker": row[1],
                "name": row[2],
                "sector_group": row[3],
                "country": row[4],
            }
            for row in rows
        ]

    def upsert_sources(self, sources: Sequence[SourceRecord]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO sources
                (
                    source_id, company_id, source_type, source_date, url,
                    local_path, extraction_status, retrieved_at, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        s.source_id,
                        s.company_id,
                        s.source_type,
                        s.source_date,
                        str(s.url),
                        s.local_path,
                        s.extraction_status,
                        s.retrieved_at,
                        s.error_message,
                    )
                    for s in sources
                ],
            )

    def insert_relationship_candidates(self, candidates: Sequence[RelationshipCandidate]) -> None:
        with self.connect() as connection:
            for index, candidate in enumerate(candidates):
                evidence_id = f"{candidate.source_id}-evidence-{index}"
                relationship_id = f"{candidate.source_id}-relationship-{index}"
                connection.execute(
                    """
                    INSERT OR REPLACE INTO evidence_items
                    (
                        evidence_id, source_id, company_id, evidence_type,
                        extracted_text, parser_method, confidence, source_location
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        candidate.source_id,
                        candidate.company_id,
                        candidate.evidence_type,
                        candidate.extracted_text,
                        candidate.parser_method,
                        candidate.confidence,
                        None,
                    ),
                )
                connection.execute(
                    """
                    INSERT OR REPLACE INTO relationships
                    (
                        relationship_id, buyer_company_id, seller_company_id,
                        relationship_type, annual_flow_low, annual_flow_base,
                        annual_flow_high, dependency_percentage, confidence_score,
                        evidence_item_ids, estimation_method, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relationship_id,
                        "unknown_buyer",
                        candidate.company_id,
                        candidate.evidence_type,
                        candidate.amount,
                        candidate.amount or 0.0,
                        candidate.amount,
                        candidate.percentage,
                        candidate.confidence,
                        json.dumps([evidence_id]),
                        "exact" if candidate.amount else "percentage-derived",
                        "Automated candidate requires buyer resolution when buyer is not named.",
                    ),
                )

    def save_candidate(
        self, candidate: RelationshipCandidateV2, verification: VerificationResult
    ) -> None:
        now = datetime.now(UTC).isoformat()
        verification_json = asdict(verification)
        verification_json["checks"] = [asdict(check) for check in verification.checks]
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO relationship_candidates
                (candidate_id, source_id, status, candidate_json, verification_json,
                 mechanically_valid, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.source_id,
                    candidate.status.value,
                    json.dumps(candidate.model_dump(mode="json")),
                    json.dumps(verification_json),
                    verification.mechanically_valid,
                    now,
                ),
            )

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT candidate_id, source_id, status, candidate_json,
                       verification_json, mechanically_valid, saved_at
                FROM relationship_candidates
                WHERE candidate_id = ?
                """,
                [candidate_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "candidate_id": row[0],
            "source_id": row[1],
            "status": row[2],
            "candidate": json.loads(row[3]),
            "verification": json.loads(row[4]),
            "mechanically_valid": row[5],
            "saved_at": str(row[6]),
        }

    def record_candidate_audit(self, event: AuditEvent) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO candidate_audit_log
                (audit_id, candidate_id, from_status, to_status, reviewer_id, reason,
                 verification_valid, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    event.candidate_id,
                    event.from_status.value if event.from_status else None,
                    event.to_status.value,
                    event.reviewer_id,
                    event.reason,
                    event.verification_valid,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_candidate_audit(self, candidate_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT audit_id, candidate_id, from_status, to_status, reviewer_id,
                       reason, verification_valid, created_at
                FROM candidate_audit_log
                WHERE candidate_id = ?
                ORDER BY created_at, audit_id
                """,
                [candidate_id],
            ).fetchall()
        return [
            {
                "audit_id": row[0],
                "candidate_id": row[1],
                "from_status": row[2],
                "to_status": row[3],
                "reviewer_id": row[4],
                "reason": row[5],
                "verification_valid": row[6],
                "created_at": str(row[7]),
            }
            for row in rows
        ]
