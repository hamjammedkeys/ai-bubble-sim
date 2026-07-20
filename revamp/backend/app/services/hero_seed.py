"""Transaction-safe initialization of the verified hero graph."""

import logging
from datetime import date
from typing import Literal

from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import Document, Edge, Entity, Passage, Scenario

logger = logging.getLogger(__name__)

HERO_SCENARIO_NAME = "OpenAI credit event"
HERO_ENTITY_NAMES = frozenset({"Microsoft", "OpenAI", "CoreWeave", "Nvidia", "TSMC", "ASML"})

SeedOutcome = Literal["seeded", "already_seeded", "preserved_partial"]


def _database_has_any_graph_data(session: Session) -> bool:
    return any(
        session.query(model).first() is not None
        for model in (Document, Passage, Entity, Edge, Scenario)
    )


def _complete_hero_seed_exists(session: Session) -> bool:
    sentinel_exists = (
        session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).first() is not None
    )
    if not sentinel_exists:
        return False

    entity_count = session.query(Entity).filter(Entity.name.in_(HERO_ENTITY_NAMES)).count()
    return entity_count == len(HERO_ENTITY_NAMES)


def seed_hero_if_empty(session: Session) -> SeedOutcome:
    """Insert the hero graph only when the caller's transaction is empty."""
    if _complete_hero_seed_exists(session):
        return "already_seeded"
    if _database_has_any_graph_data(session):
        logger.warning("Hero seed skipped because the database already contains graph data")
        return "preserved_partial"

    _insert_hero_graph(session)
    return "seeded"


def initialize_database() -> SeedOutcome:
    """Create missing tables and seed the hero graph in one transaction."""
    init_db()
    with SessionLocal.begin() as session:
        return seed_hero_if_empty(session)


def _insert_hero_graph(session: Session) -> None:
    """Insert the verified hero dataset without committing the caller's transaction."""

    def entity(name: str, entity_type: str) -> Entity:
        value = Entity(name=name, entity_type=entity_type, aliases=[])
        session.add(value)
        session.flush()
        return value

    # Layered economy: investor -> model -> cloud -> gpu -> foundry -> equipment
    msft = entity("Microsoft", "investor")
    openai = entity("OpenAI", "model_company")
    coreweave = entity("CoreWeave", "cloud_provider")
    nvidia = entity("Nvidia", "gpu_maker")
    tsmc = entity("TSMC", "foundry")
    asml = entity("ASML", "equipment_maker")

    def document(**kwargs) -> Document:
        value = Document(**kwargs)
        session.add(value)
        session.flush()
        return value

    # Primary-source documents (real filings).
    doc_msft = document(
        title="Microsoft 10-Q, quarter ended March 31, 2026",
        filing_type="10-Q",
        company="Microsoft",
        url="https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm",
        filed_date=date(2026, 4, 29),
        period="Q3 FY2026",
        raw_text=(
            "We have an investment of approximately 27 percent of OpenAI on an as-converted "
            "basis accounted for under the equity method of accounting. We have made total "
            "funding commitments of $13 billion, of which $11.8 billion has been funded as of "
            "March 31, 2026."
        ),
    )
    doc_cw_s1a = document(
        title="CoreWeave S-1/A",
        filing_type="S-1/A",
        company="CoreWeave",
        url="https://www.sec.gov/Archives/edgar/data/1769628/000119312525058309/d899798ds1a.htm",
        filed_date=date(2025, 3, 20),
        period="as of March 2025",
        raw_text=(
            "In March 2025, we entered into a master services agreement with OpenAI, a private "
            "company, pursuant to which OpenAI has committed to pay us up to approximately "
            "$11.9 billion through October 2030. "
            "The aggregate amount of estimated future undiscounted lease payments associated "
            "with such data-center leases is $11.9 billion."
        ),
    )
    doc_cw_10q = document(
        title="CoreWeave 10-Q, quarter ended March 31, 2026",
        filing_type="10-Q",
        company="CoreWeave",
        url="https://www.sec.gov/Archives/edgar/data/1769628/000176962826000222/0001769628-26-000222-index.htm",
        filed_date=date(2026, 5, 8),
        period="Q1 2026",
        raw_text=(
            "In May 2025, we entered into a master services agreement with OpenAI OpCo, LLC "
            "and in September 2025 an order form under this master services agreement pursuant "
            "to which OpenAI has committed to pay us up to approximately $6.5 billion through "
            "May 31, 2031."
        ),
    )

    def passage(doc: Document, text: str) -> str:
        value = Passage(document_id=doc.id, text=text)
        session.add(value)
        session.flush()
        return value.id

    def edge(
        source: Entity,
        target: Entity,
        relationship_type: str,
        *,
        metric=None,
        value=None,
        unit=None,
        period=None,
        evidence_class,
        status="approved",
        doc=None,
        passage_id=None,
        verification=None,
    ) -> None:
        session.add(
            Edge(
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=relationship_type,
                metric=metric,
                value=value,
                unit=unit,
                period=period,
                evidence_class=evidence_class,
                passage_id=passage_id,
                document_id=doc.id if doc else None,
                status=status,
                verification=verification,
            )
        )

    passed_verification = {
        "overall": "pass",
        "passage_found": True,
        "match_score": 100,
        "number_found": True,
    }

    # Solid quantified core (approved, primary-sourced).
    edge(
        msft,
        openai,
        "equity_method",
        metric="ownership_pct",
        value=27.0,
        unit="percent",
        period="as-converted, as of Mar 31, 2026 (post Oct-2025 recap)",
        evidence_class="reported",
        doc=doc_msft,
        passage_id=passage(
            doc_msft,
            "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting.",
        ),
        verification=passed_verification,
    )
    edge(
        openai,
        coreweave,
        "purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through October 2030",
        evidence_class="reported",
        doc=doc_cw_s1a,
        passage_id=passage(
            doc_cw_s1a,
            "OpenAI has committed to pay us up to approximately $11.9 billion through October 2030.",
        ),
        verification=passed_verification,
    )

    # Amber behavioural periphery (documented industry structure, never quantified).
    for source, target in ((coreweave, nvidia), (nvidia, tsmc), (tsmc, asml)):
        edge(source, target, "supplier_dependency", evidence_class="unknown")

    # Candidate awaiting review: a real second OpenAI -> CoreWeave commitment.
    edge(
        openai,
        coreweave,
        "purchase_obligation",
        metric="contract_value",
        value=6.5,
        unit="usd_billions",
        period="through May 2031",
        evidence_class="reported",
        status="candidate",
        doc=doc_cw_10q,
        passage_id=passage(
            doc_cw_10q,
            "OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031.",
        ),
        verification=passed_verification,
    )
    # Candidate to reject: an unrelated same-filing $11.9B data-center lease.
    edge(
        openai,
        coreweave,
        "purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="lease term",
        evidence_class="reported",
        status="candidate",
        doc=doc_cw_s1a,
        passage_id=passage(
            doc_cw_s1a,
            "The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion.",
        ),
        verification={
            "overall": "flag",
            "passage_found": True,
            "match_score": 100,
            "number_found": True,
            "entities_found": False,
            "note": "passage describes data-center leases, not an OpenAI commitment",
        },
    )

    session.add(
        Scenario(
            name=HERO_SCENARIO_NAME,
            description="OpenAI reports a +$10B incremental GAAP loss under severe distress.",
            shock_json={
                "origin_entity": "OpenAI",
                "kind": "gaap_loss",
                "magnitude": 10.0,
                "unit": "usd_billions",
            },
        )
    )
    session.flush()
