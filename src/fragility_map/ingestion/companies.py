from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CompanyConfig(BaseModel):
    company_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sector_group: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=2)


def load_company_configs(path: Path) -> list[CompanyConfig]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return [CompanyConfig(**item) for item in payload["companies"]]
