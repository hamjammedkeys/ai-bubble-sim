from pathlib import Path
from shutil import copyfile

from fragility_map.db.repository import FragilityRepository
from fragility_map.ingestion.official_pdfs import load_source_urls
from fragility_map.ingestion.refresh import refresh_sources


def test_load_source_urls_returns_official_sources() -> None:
    sources = load_source_urls(Path("config/source_urls.yaml"))

    assert len(sources) == 20
    assert sources[0].company_id == "msft"
    assert sources[0].source_type in {"sec_10k", "annual_report_pdf", "investor_pdf"}
    assert sources[0].extraction_status == "pending"


def test_refresh_sources_creates_schema_and_companies(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    copyfile("config/companies.yaml", tmp_path / "config" / "companies.yaml")
    copyfile("config/source_urls.yaml", tmp_path / "config" / "source_urls.yaml")

    count = refresh_sources(tmp_path)

    repo = FragilityRepository(tmp_path / "data" / "ai_fragility.duckdb")
    assert count == 20
    assert len(repo.list_companies()) == 20
