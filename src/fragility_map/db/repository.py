from collections.abc import Sequence
from pathlib import Path
from typing import Any

import duckdb

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
