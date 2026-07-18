from pathlib import Path

from fragility_map.ingestion.companies import load_company_configs


def test_load_company_configs_reads_target_universe() -> None:
    companies = load_company_configs(Path("config/companies.yaml"))

    assert len(companies) == 20
    assert companies[0].company_id == "msft"
    assert companies[0].ticker == "MSFT"
    assert companies[0].sector_group == "cloud_platform"
    assert {company.sector_group for company in companies} == {
        "cloud_platform",
        "semiconductor",
        "infrastructure",
        "semiconductor_equipment",
    }
