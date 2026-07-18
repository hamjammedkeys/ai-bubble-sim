from pathlib import Path

from fragility_map.db.repository import FragilityRepository
from fragility_map.ingestion.companies import CompanyConfig


def test_repository_creates_schema_and_upserts_companies(tmp_path: Path) -> None:
    repo = FragilityRepository(tmp_path / "test.duckdb")
    repo.create_schema()

    repo.upsert_companies(
        [
            CompanyConfig(
                company_id="msft",
                ticker="MSFT",
                name="Microsoft",
                sector_group="cloud_platform",
                country="US",
            )
        ]
    )

    companies = repo.list_companies()

    assert companies == [
        {
            "company_id": "msft",
            "ticker": "MSFT",
            "name": "Microsoft",
            "sector_group": "cloud_platform",
            "country": "US",
        }
    ]
