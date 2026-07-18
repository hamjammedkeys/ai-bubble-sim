from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl


class SourceRecord(BaseModel):
    source_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_date: date
    url: HttpUrl
    local_path: str | None = None
    extraction_status: str = "pending"
    retrieved_at: str | None = None
    error_message: str | None = None


def load_source_urls(path: Path) -> list[SourceRecord]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        SourceRecord(
            source_id=f"{item['company_id']}-{item['source_type']}-{item['source_date']}",
            **item,
        )
        for item in payload["sources"]
    ]
