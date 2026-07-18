from pathlib import Path

from fragility_map.db.repository import FragilityRepository
from fragility_map.ingestion.companies import load_company_configs
from fragility_map.ingestion.official_pdfs import load_source_urls
from fragility_map.settings import get_paths


def refresh_sources(root: Path | None = None) -> int:
    paths = get_paths(root)
    repo = FragilityRepository(paths.db_path)
    repo.create_schema()
    companies = load_company_configs(paths.root / "config" / "companies.yaml")
    sources = load_source_urls(paths.root / "config" / "source_urls.yaml")
    repo.upsert_companies(companies)
    repo.upsert_sources(sources)
    return len(companies)
