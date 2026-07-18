# AI Fragility Map Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend/data/API side of AI Fragility Map: project tooling, company universe, DuckDB schema, official-source ingestion, relationship extraction, stress model, graph export, and FastAPI endpoints.

**Architecture:** Python owns ingestion, extraction, persistence, scenario math, and graph export. DuckDB stores companies, source metadata, evidence, relationships, metrics, and scenario runs. FastAPI exposes read-only graph data and a cloud-spending slowdown scenario endpoint for the frontend.

**Tech Stack:** Python 3.11+, DuckDB, pandas, pydantic, requests, beautifulsoup4, pdfplumber, FastAPI, pytest, ruff.

## Global Constraints

- Use real public company names in the first 20-company universe.
- The initial shock source is cloud/platform buyers.
- Use official sources only: SEC filings and official company annual reports or investor PDFs.
- Do not scrape informal web sources in the MVP.
- Do not treat modeled losses as predictions.
- Confidence describes evidence quality and must not be multiplied into financial loss calculations.
- Default stress thresholds: Exposed at revenue loss >= 3% of revenue; Stressed at revenue loss >= 8% of revenue or operating income decline >= 20%; Critical when operating income turns negative, interest coverage < 2.0, or estimated annual cash loss > 25% of cash.
- Every estimate must be labeled as exact, percentage-derived, range-derived, or inferred.
- Scenario language must say "estimated impact under scenario", not "predicted loss".
- Keep `.superpowers/` untracked.

---

## Backend File Structure

```text
pyproject.toml
Makefile
.gitignore
README.md
data/
  raw/.gitkeep
  processed/.gitkeep
config/
  companies.yaml
  source_urls.yaml
src/fragility_map/
  __init__.py
  cli.py
  settings.py
  db/
    __init__.py
    schema.sql
    repository.py
  ingestion/
    __init__.py
    companies.py
    sec.py
    official_pdfs.py
    refresh.py
  extraction/
    __init__.py
    text.py
    financials.py
    relationships.py
  model/
    __init__.py
    stress.py
    graph_export.py
  api/
    __init__.py
    server.py
tests/
  fixtures/
    sec_customer_concentration.txt
    pdf_supplier_commitment.txt
  test_settings.py
  test_companies.py
  test_repository.py
  test_source_ingestion.py
  test_relationship_extraction.py
  test_stress_model.py
  test_graph_export.py
```

---

### Task 1: Python Project Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/fragility_map/__init__.py`
- Create: `src/fragility_map/settings.py`
- Create: `tests/test_settings.py`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`

**Interfaces:**
- Produces: `ProjectPaths(root, data_dir, raw_dir, processed_dir, db_path)`.
- Produces: `get_paths(root: Path | None = None) -> ProjectPaths`.

- [ ] **Step 1: Write the failing settings test**

Create `tests/test_settings.py`:

```python
from pathlib import Path

from fragility_map.settings import get_paths


def test_get_paths_uses_project_root(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    assert paths.root == tmp_path
    assert paths.data_dir == tmp_path / "data"
    assert paths.raw_dir == tmp_path / "data" / "raw"
    assert paths.processed_dir == tmp_path / "data" / "processed"
    assert paths.db_path == tmp_path / "data" / "ai_fragility.duckdb"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_settings.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map'`.

- [ ] **Step 3: Add Python package configuration**

Create `pyproject.toml`:

```toml
[project]
name = "ai-fragility-map"
version = "0.1.0"
description = "Data-first AI supply-chain fragility simulator and ripple-map dashboard."
requires-python = ">=3.11"
dependencies = [
  "beautifulsoup4>=4.12.3",
  "duckdb>=1.0.0",
  "fastapi>=0.111.0",
  "httpx>=0.27.0",
  "pandas>=2.2.2",
  "pdfplumber>=0.11.0",
  "pydantic>=2.7.0",
  "python-dotenv>=1.0.1",
  "pyyaml>=6.0.1",
  "requests>=2.32.0",
  "uvicorn>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-cov>=5.0.0",
  "ruff>=0.5.0"
]

[project.scripts]
fragility-map = "fragility_map.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fragility_map"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 4: Add settings implementation**

Create `src/fragility_map/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `src/fragility_map/settings.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    db_path: Path


def get_paths(root: Path | None = None) -> ProjectPaths:
    project_root = root or Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    return ProjectPaths(
        root=project_root,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        db_path=data_dir / "ai_fragility.duckdb",
    )
```

- [ ] **Step 5: Add backend workflow files**

Create `Makefile`:

```makefile
.PHONY: install test lint refresh api

install:
	python -m pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src tests

refresh:
	fragility-map refresh

api:
	uvicorn fragility_map.api.server:app --reload
```

Create `.gitignore`:

```gitignore
.DS_Store
.env
.pytest_cache/
.ruff_cache/
.superpowers/
__pycache__/
*.pyc
node_modules/
frontend/node_modules/
frontend/dist/
data/ai_fragility.duckdb
data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
```

Create `README.md`:

```markdown
# AI Fragility Map

AI Fragility Map is a data-first polished demo that shows estimated ripple effects from a cloud/platform AI infrastructure spending slowdown.

Backend commands:

```bash
make install
make test
make refresh
make api
```
```

Create empty files:

```text
data/raw/.gitkeep
data/processed/.gitkeep
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
pytest tests/test_settings.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml Makefile .gitignore README.md src/fragility_map/__init__.py src/fragility_map/settings.py tests/test_settings.py data/raw/.gitkeep data/processed/.gitkeep
git commit -m "chore: add backend project foundation"
```

---

### Task 2: Company Universe And DuckDB Schema

**Files:**
- Create: `config/companies.yaml`
- Create: `src/fragility_map/db/__init__.py`
- Create: `src/fragility_map/db/schema.sql`
- Create: `src/fragility_map/db/repository.py`
- Create: `src/fragility_map/ingestion/__init__.py`
- Create: `src/fragility_map/ingestion/companies.py`
- Create: `tests/test_companies.py`
- Create: `tests/test_repository.py`

**Interfaces:**
- Produces: `CompanyConfig(company_id, ticker, name, sector_group, country)`.
- Produces: `load_company_configs(path: Path) -> list[CompanyConfig]`.
- Produces: `FragilityRepository.create_schema() -> None`.
- Produces: `FragilityRepository.upsert_companies(companies: Sequence[CompanyConfig]) -> None`.
- Produces: `FragilityRepository.list_companies() -> list[dict[str, Any]]`.

- [ ] **Step 1: Write company and repository tests**

Create `tests/test_companies.py`:

```python
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
```

Create `tests/test_repository.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_companies.py tests/test_repository.py -v
```

Expected: FAIL because config and database modules do not exist.

- [ ] **Step 3: Add company universe**

Create `config/companies.yaml` with exactly these 20 records:

```yaml
companies:
  - {company_id: msft, ticker: MSFT, name: Microsoft, sector_group: cloud_platform, country: US}
  - {company_id: amzn, ticker: AMZN, name: Amazon, sector_group: cloud_platform, country: US}
  - {company_id: googl, ticker: GOOGL, name: Alphabet, sector_group: cloud_platform, country: US}
  - {company_id: meta, ticker: META, name: Meta Platforms, sector_group: cloud_platform, country: US}
  - {company_id: orcl, ticker: ORCL, name: Oracle, sector_group: cloud_platform, country: US}
  - {company_id: nvda, ticker: NVDA, name: NVIDIA, sector_group: semiconductor, country: US}
  - {company_id: amd, ticker: AMD, name: AMD, sector_group: semiconductor, country: US}
  - {company_id: avgo, ticker: AVGO, name: Broadcom, sector_group: semiconductor, country: US}
  - {company_id: mrvl, ticker: MRVL, name: Marvell Technology, sector_group: semiconductor, country: US}
  - {company_id: mu, ticker: MU, name: Micron Technology, sector_group: semiconductor, country: US}
  - {company_id: hxscl, ticker: 000660.KS, name: SK hynix, sector_group: semiconductor, country: KR}
  - {company_id: smci, ticker: SMCI, name: Super Micro Computer, sector_group: infrastructure, country: US}
  - {company_id: dell, ticker: DELL, name: Dell Technologies, sector_group: infrastructure, country: US}
  - {company_id: anet, ticker: ANET, name: Arista Networks, sector_group: infrastructure, country: US}
  - {company_id: vrt, ticker: VRT, name: Vertiv, sector_group: infrastructure, country: US}
  - {company_id: sbgsf, ticker: SU.PA, name: Schneider Electric, sector_group: infrastructure, country: FR}
  - {company_id: etn, ticker: ETN, name: Eaton, sector_group: infrastructure, country: IE}
  - {company_id: asml, ticker: ASML, name: ASML, sector_group: semiconductor_equipment, country: NL}
  - {company_id: amat, ticker: AMAT, name: Applied Materials, sector_group: semiconductor_equipment, country: US}
  - {company_id: lrcx, ticker: LRCX, name: Lam Research, sector_group: semiconductor_equipment, country: US}
```

- [ ] **Step 4: Add company loader**

Create `src/fragility_map/ingestion/__init__.py` and `src/fragility_map/db/__init__.py` as empty files.

Create `src/fragility_map/ingestion/companies.py`:

```python
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
```

- [ ] **Step 5: Add DuckDB schema and repository**

Create `src/fragility_map/db/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    sector_group TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_metrics (
    company_id TEXT NOT NULL,
    fiscal_period TEXT NOT NULL,
    revenue DOUBLE,
    cash DOUBLE,
    debt DOUBLE,
    operating_income DOUBLE,
    capital_expenditure DOUBLE,
    interest_expense DOUBLE,
    metric_source_ids TEXT,
    PRIMARY KEY (company_id, fiscal_period)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_date DATE,
    url TEXT NOT NULL,
    local_path TEXT,
    extraction_status TEXT NOT NULL,
    retrieved_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    parser_method TEXT NOT NULL,
    confidence DOUBLE NOT NULL,
    source_location TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    buyer_company_id TEXT NOT NULL,
    seller_company_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    annual_flow_low DOUBLE,
    annual_flow_base DOUBLE NOT NULL,
    annual_flow_high DOUBLE,
    dependency_percentage DOUBLE,
    confidence_score DOUBLE NOT NULL,
    evidence_item_ids TEXT NOT NULL,
    estimation_method TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scenario_runs (
    scenario_id TEXT PRIMARY KEY,
    shock_source_group TEXT NOT NULL,
    shock_percentage DOUBLE NOT NULL,
    pass_through_rate DOUBLE NOT NULL,
    propagation_factor DOUBLE NOT NULL,
    max_rounds INTEGER NOT NULL,
    estimate_mode TEXT NOT NULL,
    run_timestamp TIMESTAMP NOT NULL,
    per_company_impacts TEXT NOT NULL,
    per_edge_pulses TEXT NOT NULL
);
```

Create `src/fragility_map/db/repository.py`:

```python
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import duckdb

from fragility_map.ingestion.companies import CompanyConfig


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
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_companies.py tests/test_repository.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add config/companies.yaml src/fragility_map/db src/fragility_map/ingestion tests/test_companies.py tests/test_repository.py
git commit -m "feat: add company universe and database schema"
```

---

### Task 3: Official Source Catalog And Refresh Command

**Files:**
- Create: `config/source_urls.yaml`
- Create: `src/fragility_map/cli.py`
- Create: `src/fragility_map/ingestion/sec.py`
- Create: `src/fragility_map/ingestion/official_pdfs.py`
- Create: `src/fragility_map/ingestion/refresh.py`
- Modify: `src/fragility_map/db/repository.py`
- Create: `tests/test_source_ingestion.py`

**Interfaces:**
- Produces: `SourceRecord`.
- Produces: `load_source_urls(path: Path) -> list[SourceRecord]`.
- Produces: `refresh_sources(root: Path | None = None) -> int`.
- Produces CLI command: `fragility-map refresh`.

- [ ] **Step 1: Write source ingestion tests**

Create `tests/test_source_ingestion.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_source_ingestion.py -v
```

Expected: FAIL because source modules and source config do not exist.

- [ ] **Step 3: Add official source config**

Create `config/source_urls.yaml` with one official source per company:

```yaml
sources:
  - {company_id: msft, source_type: sec_10k, source_date: "2025-07-30", url: "https://www.sec.gov/Archives/edgar/data/789019/"}
  - {company_id: amzn, source_type: sec_10k, source_date: "2025-02-07", url: "https://www.sec.gov/Archives/edgar/data/1018724/"}
  - {company_id: googl, source_type: sec_10k, source_date: "2025-02-05", url: "https://www.sec.gov/Archives/edgar/data/1652044/"}
  - {company_id: meta, source_type: sec_10k, source_date: "2025-01-31", url: "https://www.sec.gov/Archives/edgar/data/1326801/"}
  - {company_id: orcl, source_type: sec_10k, source_date: "2025-06-20", url: "https://www.sec.gov/Archives/edgar/data/1341439/"}
  - {company_id: nvda, source_type: sec_10k, source_date: "2025-02-26", url: "https://www.sec.gov/Archives/edgar/data/1045810/"}
  - {company_id: amd, source_type: sec_10k, source_date: "2025-02-05", url: "https://www.sec.gov/Archives/edgar/data/2488/"}
  - {company_id: avgo, source_type: sec_10k, source_date: "2024-12-20", url: "https://www.sec.gov/Archives/edgar/data/1730168/"}
  - {company_id: mrvl, source_type: sec_10k, source_date: "2025-03-14", url: "https://www.sec.gov/Archives/edgar/data/1835632/"}
  - {company_id: mu, source_type: sec_10k, source_date: "2024-10-04", url: "https://www.sec.gov/Archives/edgar/data/723125/"}
  - {company_id: hxscl, source_type: annual_report_pdf, source_date: "2025-03-31", url: "https://www.skhynix.com/ir/UI-FR-IR68"}
  - {company_id: smci, source_type: sec_10k, source_date: "2024-08-30", url: "https://www.sec.gov/Archives/edgar/data/1375365/"}
  - {company_id: dell, source_type: sec_10k, source_date: "2025-03-25", url: "https://www.sec.gov/Archives/edgar/data/1571996/"}
  - {company_id: anet, source_type: sec_10k, source_date: "2025-02-14", url: "https://www.sec.gov/Archives/edgar/data/1596532/"}
  - {company_id: vrt, source_type: sec_10k, source_date: "2025-02-21", url: "https://www.sec.gov/Archives/edgar/data/1674101/"}
  - {company_id: sbgsf, source_type: annual_report_pdf, source_date: "2025-03-27", url: "https://www.se.com/ww/en/about-us/investor-relations/"}
  - {company_id: etn, source_type: sec_10k, source_date: "2025-02-21", url: "https://www.sec.gov/Archives/edgar/data/1551182/"}
  - {company_id: asml, source_type: annual_report_pdf, source_date: "2025-02-12", url: "https://www.asml.com/en/investors/annual-report"}
  - {company_id: amat, source_type: sec_10k, source_date: "2024-12-13", url: "https://www.sec.gov/Archives/edgar/data/6951/"}
  - {company_id: lrcx, source_type: sec_10k, source_date: "2024-08-23", url: "https://www.sec.gov/Archives/edgar/data/707549/"}
```

- [ ] **Step 4: Add source loader, refresh command, and repository persistence**

Create `src/fragility_map/ingestion/official_pdfs.py`:

```python
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
```

Create `src/fragility_map/ingestion/sec.py`:

```python
SEC_USER_AGENT = "AI Fragility Map demo contact@example.com"
```

Create `src/fragility_map/ingestion/refresh.py`:

```python
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
```

Create `src/fragility_map/cli.py`:

```python
import argparse

from fragility_map.ingestion.refresh import refresh_sources


def main() -> None:
    parser = argparse.ArgumentParser(prog="fragility-map")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh")
    args = parser.parse_args()
    if args.command == "refresh":
        count = refresh_sources()
        print(f"Refreshed {count} companies")
```

Add to `src/fragility_map/db/repository.py`:

```python
from fragility_map.ingestion.official_pdfs import SourceRecord

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
```

- [ ] **Step 5: Verify refresh**

Run:

```bash
pytest tests/test_source_ingestion.py tests/test_repository.py -v
fragility-map refresh
```

Expected: tests PASS and command prints `Refreshed 20 companies`.

- [ ] **Step 6: Commit**

```bash
git add config/source_urls.yaml src/fragility_map/cli.py src/fragility_map/ingestion/sec.py src/fragility_map/ingestion/official_pdfs.py src/fragility_map/ingestion/refresh.py src/fragility_map/db/repository.py tests/test_source_ingestion.py
git commit -m "feat: add official source refresh command"
```

---

### Task 4: Evidence Extraction

**Files:**
- Create: `src/fragility_map/extraction/__init__.py`
- Create: `src/fragility_map/extraction/text.py`
- Create: `src/fragility_map/extraction/financials.py`
- Create: `src/fragility_map/extraction/relationships.py`
- Modify: `src/fragility_map/db/repository.py`
- Create: `tests/fixtures/sec_customer_concentration.txt`
- Create: `tests/fixtures/pdf_supplier_commitment.txt`
- Create: `tests/test_relationship_extraction.py`

**Interfaces:**
- Produces: `RelationshipCandidate`.
- Produces: `extract_relationship_candidates(company_id: str, source_id: str, text: str) -> list[RelationshipCandidate]`.
- Produces: `estimate_confidence(evidence_type: str, has_numeric_value: bool) -> float`.

- [ ] **Step 1: Write fixtures and tests**

Create `tests/fixtures/sec_customer_concentration.txt`:

```text
One customer accounted for approximately 19% of total revenue for fiscal 2025. The customer purchases advanced AI systems for data center deployments.
```

Create `tests/fixtures/pdf_supplier_commitment.txt`:

```text
We have purchase commitments of $4.0 billion related to advanced compute components and data center infrastructure suppliers.
```

Create `tests/test_relationship_extraction.py`:

```python
from pathlib import Path

from fragility_map.extraction.relationships import (
    estimate_confidence,
    extract_relationship_candidates,
)


def test_extracts_customer_concentration_candidate() -> None:
    text = Path("tests/fixtures/sec_customer_concentration.txt").read_text(encoding="utf-8")
    candidates = extract_relationship_candidates("nvda", "nvda-sec_10k-2025-02-26", text)

    assert len(candidates) == 1
    assert candidates[0].evidence_type == "customer_concentration"
    assert candidates[0].percentage == 0.19
    assert candidates[0].confidence == 0.9


def test_extracts_purchase_commitment_candidate() -> None:
    text = Path("tests/fixtures/pdf_supplier_commitment.txt").read_text(encoding="utf-8")
    candidates = extract_relationship_candidates("msft", "msft-investor_pdf-2025-07-30", text)

    assert len(candidates) == 1
    assert candidates[0].evidence_type == "purchase_commitment"
    assert candidates[0].amount == 4_000_000_000
    assert candidates[0].confidence == 1.0


def test_confidence_rules_do_not_mix_with_economic_impact() -> None:
    assert estimate_confidence("exact_amount", True) == 1.0
    assert estimate_confidence("customer_concentration", True) == 0.9
    assert estimate_confidence("relationship_disclosure", False) == 0.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_relationship_extraction.py -v
```

Expected: FAIL because extraction modules do not exist.

- [ ] **Step 3: Add extraction implementation**

Create `src/fragility_map/extraction/__init__.py` as an empty file.

Create `src/fragility_map/extraction/relationships.py`:

```python
import re

from pydantic import BaseModel, Field


class RelationshipCandidate(BaseModel):
    company_id: str
    source_id: str
    evidence_type: str
    extracted_text: str
    parser_method: str
    confidence: float = Field(ge=0.0, le=1.0)
    percentage: float | None = None
    amount: float | None = None


def estimate_confidence(evidence_type: str, has_numeric_value: bool) -> float:
    if evidence_type == "exact_amount" and has_numeric_value:
        return 1.0
    if evidence_type == "customer_concentration" and has_numeric_value:
        return 0.9
    if evidence_type == "relationship_disclosure" and has_numeric_value:
        return 0.6
    return 0.3


def _parse_money_amount(text: str) -> float | None:
    match = re.search(r"\$([0-9]+(?:\.[0-9]+)?)\s*(billion|million)", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    scale = 1_000_000_000 if match.group(2).lower() == "billion" else 1_000_000
    return value * scale


def _parse_percentage(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s+of\s+(?:total\s+)?revenue", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1)) / 100


def extract_relationship_candidates(company_id: str, source_id: str, text: str) -> list[RelationshipCandidate]:
    normalized = " ".join(text.split())
    candidates: list[RelationshipCandidate] = []
    if "customer" in normalized.lower() and "revenue" in normalized.lower():
        percentage = _parse_percentage(normalized)
        candidates.append(
            RelationshipCandidate(
                company_id=company_id,
                source_id=source_id,
                evidence_type="customer_concentration",
                extracted_text=normalized,
                parser_method="regex_customer_revenue_percentage",
                confidence=estimate_confidence("customer_concentration", percentage is not None),
                percentage=percentage,
            )
        )
    if "purchase commitments" in normalized.lower():
        amount = _parse_money_amount(normalized)
        candidates.append(
            RelationshipCandidate(
                company_id=company_id,
                source_id=source_id,
                evidence_type="purchase_commitment",
                extracted_text=normalized,
                parser_method="regex_purchase_commitment_amount",
                confidence=estimate_confidence("exact_amount", amount is not None),
                amount=amount,
            )
        )
    return candidates
```

Create `src/fragility_map/extraction/text.py`:

```python
from pathlib import Path

import pdfplumber


def extract_text_from_pdf(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)
```

Create `src/fragility_map/extraction/financials.py`:

```python
from pydantic import BaseModel


class FinancialMetricSnapshot(BaseModel):
    company_id: str
    fiscal_period: str
    revenue: float | None = None
    cash: float | None = None
    debt: float | None = None
    operating_income: float | None = None
    capital_expenditure: float | None = None
    interest_expense: float | None = None
    metric_source_ids: list[str] = []
```

- [ ] **Step 4: Extend repository for candidates**

Add to `src/fragility_map/db/repository.py`:

```python
import json

from fragility_map.extraction.relationships import RelationshipCandidate

    def insert_relationship_candidates(self, candidates: Sequence[RelationshipCandidate]) -> None:
        with self.connect() as connection:
            for index, candidate in enumerate(candidates):
                evidence_id = f"{candidate.source_id}-evidence-{index}"
                relationship_id = f"{candidate.source_id}-relationship-{index}"
                connection.execute(
                    """
                    INSERT OR REPLACE INTO evidence_items
                    (evidence_id, source_id, company_id, evidence_type, extracted_text, parser_method, confidence, source_location)
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
                    (relationship_id, buyer_company_id, seller_company_id, relationship_type, annual_flow_low, annual_flow_base, annual_flow_high, dependency_percentage, confidence_score, evidence_item_ids, estimation_method, notes)
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
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
pytest tests/test_relationship_extraction.py -v
```

Expected: PASS.

Commit:

```bash
git add src/fragility_map/extraction src/fragility_map/db/repository.py tests/fixtures tests/test_relationship_extraction.py
git commit -m "feat: extract relationship evidence from official text"
```

---

### Task 5: Stress Scenario Model

**Files:**
- Create: `src/fragility_map/model/__init__.py`
- Create: `src/fragility_map/model/stress.py`
- Create: `tests/test_stress_model.py`

**Interfaces:**
- Produces: `CompanyFinancials`, `NetworkRelationship`, `ScenarioConfig`, `CompanyImpact`, `EdgePulse`, `ScenarioResult`.
- Produces: `run_cloud_spending_slowdown(companies, relationships, config) -> ScenarioResult`.

- [ ] **Step 1: Write failing stress model tests**

Create `tests/test_stress_model.py`:

```python
from fragility_map.model.stress import (
    CompanyFinancials,
    NetworkRelationship,
    ScenarioConfig,
    run_cloud_spending_slowdown,
)


def test_direct_loss_ignores_confidence_score() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "nvda": CompanyFinancials("nvda", "NVIDIA", "semiconductor", 50, 15, 5, 20, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "nvda", 10, 0.3, "inferred")]

    result = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.30, 0.80, 0.50, 2),
    )

    assert result.edge_pulses[0].revenue_loss == 2.4
    assert result.company_impacts["nvda"].revenue_loss == 2.4
    assert result.company_impacts["nvda"].stress_status == "exposed"


def test_critical_when_operating_income_turns_negative() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "smci": CompanyFinancials("smci", "Supermicro", "infrastructure", 20, 2, 1, 1, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "smci", 10, 0.9, "percentage-derived")]

    result = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.40, 1.00, 0.50, 1),
    )

    assert result.company_impacts["smci"].stress_status == "critical"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_stress_model.py -v
```

Expected: FAIL because model modules do not exist.

- [ ] **Step 3: Add model implementation**

Create `src/fragility_map/model/__init__.py` as an empty file.

Create `src/fragility_map/model/stress.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyFinancials:
    company_id: str
    name: str
    sector_group: str
    revenue: float
    cash: float
    debt: float
    operating_income: float
    interest_expense: float


@dataclass(frozen=True)
class NetworkRelationship:
    relationship_id: str
    buyer_company_id: str
    seller_company_id: str
    annual_flow_base: float
    confidence_score: float
    estimation_method: str


@dataclass(frozen=True)
class ScenarioConfig:
    shock_percentage: float
    pass_through_rate: float
    propagation_factor: float
    max_rounds: int


@dataclass(frozen=True)
class EdgePulse:
    relationship_id: str
    buyer_company_id: str
    seller_company_id: str
    round_index: int
    revenue_loss: float


@dataclass(frozen=True)
class CompanyImpact:
    company_id: str
    revenue_loss: float
    operating_income_loss: float
    new_operating_income: float
    stress_status: str


@dataclass(frozen=True)
class ScenarioResult:
    company_impacts: dict[str, CompanyImpact]
    edge_pulses: list[EdgePulse]


def _stress_status(company: CompanyFinancials, revenue_loss: float) -> str:
    revenue_loss_ratio = revenue_loss / company.revenue if company.revenue else 0.0
    operating_income_loss = revenue_loss * 0.5
    new_operating_income = company.operating_income - operating_income_loss
    operating_income_decline = operating_income_loss / company.operating_income if company.operating_income else 0.0
    interest_coverage = new_operating_income / company.interest_expense if company.interest_expense else float("inf")
    if new_operating_income < 0 or interest_coverage < 2.0 or operating_income_loss > company.cash * 0.25:
        return "critical"
    if revenue_loss_ratio >= 0.08 or operating_income_decline >= 0.20:
        return "stressed"
    if revenue_loss_ratio >= 0.03:
        return "exposed"
    return "stable"


def run_cloud_spending_slowdown(
    companies: dict[str, CompanyFinancials],
    relationships: list[NetworkRelationship],
    config: ScenarioConfig,
) -> ScenarioResult:
    losses_by_company = {company_id: 0.0 for company_id in companies}
    edge_pulses: list[EdgePulse] = []
    active_shocks = {
        company_id: config.shock_percentage
        for company_id, company in companies.items()
        if company.sector_group == "cloud_platform"
    }
    for round_index in range(config.max_rounds):
        next_shocks: dict[str, float] = {}
        for relationship in relationships:
            buyer_shock = active_shocks.get(relationship.buyer_company_id, 0.0)
            if buyer_shock <= 0:
                continue
            revenue_loss = relationship.annual_flow_base * buyer_shock * config.pass_through_rate
            if revenue_loss <= 0.000001:
                continue
            losses_by_company[relationship.seller_company_id] += revenue_loss
            edge_pulses.append(
                EdgePulse(
                    relationship.relationship_id,
                    relationship.buyer_company_id,
                    relationship.seller_company_id,
                    round_index,
                    revenue_loss,
                )
            )
            seller = companies[relationship.seller_company_id]
            seller_loss_ratio = revenue_loss / seller.revenue if seller.revenue else 0.0
            next_shocks[relationship.seller_company_id] = max(
                next_shocks.get(relationship.seller_company_id, 0.0),
                seller_loss_ratio * config.propagation_factor,
            )
        active_shocks = next_shocks
        if not active_shocks:
            break
    return ScenarioResult(
        company_impacts={
            company_id: CompanyImpact(
                company_id,
                revenue_loss,
                revenue_loss * 0.5,
                company.operating_income - revenue_loss * 0.5,
                _stress_status(company, revenue_loss),
            )
            for company_id, company in companies.items()
            for revenue_loss in [losses_by_company[company_id]]
        },
        edge_pulses=edge_pulses,
    )
```

- [ ] **Step 4: Verify and commit**

Run:

```bash
pytest tests/test_stress_model.py -v
```

Expected: PASS.

Commit:

```bash
git add src/fragility_map/model tests/test_stress_model.py
git commit -m "feat: add cloud spending shock model"
```

---

### Task 6: Graph Export And FastAPI

**Files:**
- Create: `src/fragility_map/model/graph_export.py`
- Create: `src/fragility_map/api/__init__.py`
- Create: `src/fragility_map/api/server.py`
- Create: `tests/test_graph_export.py`

**Interfaces:**
- Produces: `build_graph_payload(companies, relationships, scenario_result) -> dict`.
- Produces API endpoints: `GET /api/graph`, `POST /api/scenario/cloud-slowdown`.
- Frontend consumes graph JSON with `nodes`, `edges`, `summary`, and `pulses`.

- [ ] **Step 1: Write graph export test**

Create `tests/test_graph_export.py`:

```python
from fragility_map.model.graph_export import build_graph_payload
from fragility_map.model.stress import (
    CompanyFinancials,
    CompanyImpact,
    EdgePulse,
    NetworkRelationship,
    ScenarioResult,
)


def test_build_graph_payload_labels_estimates_and_status() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "nvda": CompanyFinancials("nvda", "NVIDIA", "semiconductor", 50, 15, 5, 20, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "nvda", 10, 0.9, "percentage-derived")]
    scenario = ScenarioResult(
        {
            "msft": CompanyImpact("msft", 0, 0, 30, "stable"),
            "nvda": CompanyImpact("nvda", 2.4, 1.2, 18.8, "exposed"),
        },
        [EdgePulse("edge-1", "msft", "nvda", 0, 2.4)],
    )

    payload = build_graph_payload(companies, relationships, scenario)

    assert payload["nodes"][1]["data"]["label"] == "NVIDIA"
    assert payload["nodes"][1]["data"]["stressStatus"] == "exposed"
    assert payload["edges"][0]["data"]["estimateMethod"] == "percentage-derived"
    assert payload["summary"]["scenarioLanguage"] == "estimated impact under scenario"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_graph_export.py -v
```

Expected: FAIL because graph export does not exist.

- [ ] **Step 3: Add graph export**

Create `src/fragility_map/model/graph_export.py`:

```python
from fragility_map.model.stress import CompanyFinancials, NetworkRelationship, ScenarioResult


def build_graph_payload(
    companies: dict[str, CompanyFinancials],
    relationships: list[NetworkRelationship],
    scenario_result: ScenarioResult,
) -> dict:
    return {
        "nodes": [
            {
                "data": {
                    "id": company.company_id,
                    "label": company.name,
                    "sectorGroup": company.sector_group,
                    "revenue": company.revenue,
                    "revenueLoss": scenario_result.company_impacts[company.company_id].revenue_loss,
                    "stressStatus": scenario_result.company_impacts[company.company_id].stress_status,
                }
            }
            for company in companies.values()
        ],
        "edges": [
            {
                "data": {
                    "id": relationship.relationship_id,
                    "source": relationship.buyer_company_id,
                    "target": relationship.seller_company_id,
                    "annualFlowBase": relationship.annual_flow_base,
                    "confidenceScore": relationship.confidence_score,
                    "estimateMethod": relationship.estimation_method,
                }
            }
            for relationship in relationships
        ],
        "pulses": [
            {
                "relationshipId": pulse.relationship_id,
                "source": pulse.buyer_company_id,
                "target": pulse.seller_company_id,
                "roundIndex": pulse.round_index,
                "revenueLoss": pulse.revenue_loss,
            }
            for pulse in scenario_result.edge_pulses
        ],
        "summary": {
            "scenarioLanguage": "estimated impact under scenario",
            "totalRevenueLost": sum(i.revenue_loss for i in scenario_result.company_impacts.values()),
            "stressedCompanyCount": sum(
                1 for i in scenario_result.company_impacts.values() if i.stress_status in {"stressed", "critical"}
            ),
        },
    }
```

- [ ] **Step 4: Add FastAPI server**

Create `src/fragility_map/api/__init__.py` as an empty file.

Create `src/fragility_map/api/server.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

from fragility_map.model.graph_export import build_graph_payload
from fragility_map.model.stress import CompanyFinancials, NetworkRelationship, ScenarioConfig, run_cloud_spending_slowdown

app = FastAPI(title="AI Fragility Map API")


class ScenarioRequest(BaseModel):
    shock_percentage: float = Field(default=0.30, ge=0.0, le=1.0)
    pass_through_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    propagation_factor: float = Field(default=0.50, ge=0.0, le=1.0)
    max_rounds: int = Field(default=3, ge=1, le=3)


def demo_companies() -> dict[str, CompanyFinancials]:
    return {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 245_000, 75_000, 97_000, 110_000, 2_000),
        "amzn": CompanyFinancials("amzn", "Amazon", "cloud_platform", 638_000, 89_000, 135_000, 68_000, 3_000),
        "googl": CompanyFinancials("googl", "Alphabet", "cloud_platform", 350_000, 110_000, 30_000, 115_000, 1_000),
        "meta": CompanyFinancials("meta", "Meta Platforms", "cloud_platform", 164_000, 70_000, 37_000, 70_000, 500),
        "orcl": CompanyFinancials("orcl", "Oracle", "cloud_platform", 53_000, 11_000, 88_000, 18_000, 4_000),
        "nvda": CompanyFinancials("nvda", "NVIDIA", "semiconductor", 130_000, 43_000, 11_000, 81_000, 250),
        "amd": CompanyFinancials("amd", "AMD", "semiconductor", 26_000, 6_000, 3_000, 1_900, 120),
        "smci": CompanyFinancials("smci", "Supermicro", "infrastructure", 15_000, 2_000, 2_000, 1_200, 80),
        "anet": CompanyFinancials("anet", "Arista Networks", "infrastructure", 7_000, 6_000, 0, 2_800, 0),
        "vrt": CompanyFinancials("vrt", "Vertiv", "infrastructure", 8_000, 800, 3_000, 1_000, 250),
        "asml": CompanyFinancials("asml", "ASML", "semiconductor_equipment", 30_000, 7_000, 5_000, 9_000, 100),
        "amat": CompanyFinancials("amat", "Applied Materials", "semiconductor_equipment", 27_000, 8_000, 6_000, 8_000, 250),
    }


def demo_relationships() -> list[NetworkRelationship]:
    return [
        NetworkRelationship("msft-nvda", "msft", "nvda", 12_000, 0.6, "inferred"),
        NetworkRelationship("amzn-nvda", "amzn", "nvda", 10_000, 0.6, "inferred"),
        NetworkRelationship("googl-nvda", "googl", "nvda", 8_000, 0.6, "inferred"),
        NetworkRelationship("meta-nvda", "meta", "nvda", 9_000, 0.6, "inferred"),
        NetworkRelationship("orcl-nvda", "orcl", "nvda", 4_000, 0.6, "inferred"),
        NetworkRelationship("msft-smci", "msft", "smci", 3_000, 0.6, "inferred"),
        NetworkRelationship("amzn-anet", "amzn", "anet", 2_000, 0.6, "inferred"),
        NetworkRelationship("googl-vrt", "googl", "vrt", 1_500, 0.6, "inferred"),
        NetworkRelationship("nvda-asml", "nvda", "asml", 2_000, 0.3, "inferred"),
        NetworkRelationship("nvda-amat", "nvda", "amat", 1_500, 0.3, "inferred"),
    ]


@app.get("/api/graph")
def get_graph() -> dict:
    companies = demo_companies()
    relationships = demo_relationships()
    scenario = run_cloud_spending_slowdown(companies, relationships, ScenarioConfig(0.30, 0.80, 0.50, 3))
    return build_graph_payload(companies, relationships, scenario)


@app.post("/api/scenario/cloud-slowdown")
def run_scenario(request: ScenarioRequest) -> dict:
    companies = demo_companies()
    relationships = demo_relationships()
    scenario = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(request.shock_percentage, request.pass_through_rate, request.propagation_factor, request.max_rounds),
    )
    return build_graph_payload(companies, relationships, scenario)
```

- [ ] **Step 5: Verify API**

Run:

```bash
pytest tests/test_graph_export.py tests/test_stress_model.py -v
uvicorn fragility_map.api.server:app --port 8000
```

In another terminal:

```bash
curl http://127.0.0.1:8000/api/graph
```

Expected: JSON contains `nodes`, `edges`, `pulses`, and `summary`.

- [ ] **Step 6: Commit**

```bash
git add src/fragility_map/model/graph_export.py src/fragility_map/api tests/test_graph_export.py
git commit -m "feat: expose scenario graph api"
```

---

## Backend Self-Review

- Spec coverage: company universe, official source catalog, extraction, DuckDB schema, scenario math, graph payload, and API endpoints are covered.
- Scan result: plan contains concrete files, commands, interfaces, tests, and code blocks for code-changing steps.
- Type consistency: `CompanyConfig`, `SourceRecord`, `RelationshipCandidate`, `CompanyFinancials`, `NetworkRelationship`, `ScenarioConfig`, `ScenarioResult`, and graph payload fields are introduced before use.

## Execution Handoff

Backend plan complete and saved to `docs/superpowers/plans/2026-07-18-ai-fragility-map-backend.md`.
