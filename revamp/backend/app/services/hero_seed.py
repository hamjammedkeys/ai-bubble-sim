"""Transaction-safe initialization of the verified hero graph."""

import logging
from datetime import date
from typing import Literal

from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import Document, Edge, Entity, Passage, Scenario

logger = logging.getLogger(__name__)

HERO_SCENARIO_NAME = "OpenAI credit event"
HERO_SCENARIO_DESCRIPTION = "OpenAI reports a +$10B incremental GAAP loss under severe distress."
HERO_SCENARIO_SHOCK = {
    "origin_entity": "OpenAI",
    "kind": "gaap_loss",
    "magnitude": 10.0,
    "unit": "usd_billions",
}
HERO_ENTITY_TYPES = {
    "Microsoft": "investor",
    "OpenAI": "model_company",
    "CoreWeave": "cloud_provider",
    "Nvidia": "gpu_maker",
    "TSMC": "foundry",
    "ASML": "equipment_maker",
}

MSFT_DOCUMENT_TITLE = "Microsoft 10-Q, quarter ended March 31, 2026"
CW_S1A_DOCUMENT_TITLE = "CoreWeave S-1/A"
CW_10Q_DOCUMENT_TITLE = "CoreWeave 10-Q, quarter ended March 31, 2026"
MSFT_PASSAGE = "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting."
CW_119_PASSAGE = (
    "OpenAI has committed to pay us up to approximately $11.9 billion through October 2030."
)
CW_65_PASSAGE = (
    "OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031."
)
CW_LEASE_PASSAGE = "The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion."

HERO_DOCUMENT_IDENTITIES = (
    {
        "title": MSFT_DOCUMENT_TITLE,
        "filing_type": "10-Q",
        "company": "Microsoft",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm",
        "filed_date": date(2026, 4, 29),
        "period": "Q3 FY2026",
        "raw_text": "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting. We have made total funding commitments of $13 billion, of which $11.8 billion has been funded as of March 31, 2026.",
    },
    {
        "title": CW_S1A_DOCUMENT_TITLE,
        "filing_type": "S-1/A",
        "company": "CoreWeave",
        "url": "https://www.sec.gov/Archives/edgar/data/1769628/000119312525058309/d899798ds1a.htm",
        "filed_date": date(2025, 3, 20),
        "period": "as of March 2025",
        "raw_text": "In March 2025, we entered into a master services agreement with OpenAI, a private company, pursuant to which OpenAI has committed to pay us up to approximately $11.9 billion through October 2030. The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion.",
    },
    {
        "title": CW_10Q_DOCUMENT_TITLE,
        "filing_type": "10-Q",
        "company": "CoreWeave",
        "url": "https://www.sec.gov/Archives/edgar/data/1769628/000176962826000222/0001769628-26-000222-index.htm",
        "filed_date": date(2026, 5, 8),
        "period": "Q1 2026",
        "raw_text": "In May 2025, we entered into a master services agreement with OpenAI OpCo, LLC and in September 2025 an order form under this master services agreement pursuant to which OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031.",
    },
)

HERO_PASSAGE_ASSOCIATIONS = (
    (MSFT_DOCUMENT_TITLE, MSFT_PASSAGE),
    (CW_S1A_DOCUMENT_TITLE, CW_119_PASSAGE),
    (CW_10Q_DOCUMENT_TITLE, CW_65_PASSAGE),
    (CW_S1A_DOCUMENT_TITLE, CW_LEASE_PASSAGE),
)

PASS_VERIFICATION = {
    "overall": "pass",
    "passage_found": True,
    "match_score": 100,
    "number_found": True,
}
FLAG_VERIFICATION = {
    "overall": "flag",
    "passage_found": True,
    "match_score": 100,
    "number_found": True,
    "entities_found": False,
    "note": "passage describes data-center leases, not an OpenAI commitment",
}

# source, target, relationship, metric, value, unit, period, evidence, status,
# document title, passage text, verification
HERO_EDGE_SIGNATURES = (
    ("Microsoft", "OpenAI", "equity_method", "ownership_pct", 27.0, "percent", "as-converted, as of Mar 31, 2026 (post Oct-2025 recap)", "reported", "approved", MSFT_DOCUMENT_TITLE, MSFT_PASSAGE, PASS_VERIFICATION),
    ("OpenAI", "CoreWeave", "purchase_obligation", "contract_value", 11.9, "usd_billions", "through October 2030", "reported", "approved", CW_S1A_DOCUMENT_TITLE, CW_119_PASSAGE, PASS_VERIFICATION),
    ("CoreWeave", "Nvidia", "supplier_dependency", None, None, None, None, "unknown", "approved", None, None, None),
    ("Nvidia", "TSMC", "supplier_dependency", None, None, None, None, "unknown", "approved", None, None, None),
    ("TSMC", "ASML", "supplier_dependency", None, None, None, None, "unknown", "approved", None, None, None),
    ("OpenAI", "CoreWeave", "purchase_obligation", "contract_value", 6.5, "usd_billions", "through May 2031", "reported", "candidate", CW_10Q_DOCUMENT_TITLE, CW_65_PASSAGE, PASS_VERIFICATION),
    ("OpenAI", "CoreWeave", "purchase_obligation", "contract_value", 11.9, "usd_billions", "lease term", "reported", "candidate", CW_S1A_DOCUMENT_TITLE, CW_LEASE_PASSAGE, FLAG_VERIFICATION),
)

SeedOutcome = Literal["seeded", "already_seeded", "preserved_partial"]


def _database_has_any_graph_data(session: Session) -> bool:
    return any(
        session.query(model).first() is not None
        for model in (Document, Passage, Entity, Edge, Scenario)
    )


def _complete_hero_seed_exists(session: Session) -> bool:
    scenarios = session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).all()
    if not any(
        scenario.description == HERO_SCENARIO_DESCRIPTION
        and scenario.shock_json == HERO_SCENARIO_SHOCK
        for scenario in scenarios
    ):
        return False

    entities = session.query(Entity).filter(Entity.name.in_(HERO_ENTITY_TYPES)).all()
    entity_ids = {
        entity.name: entity.id
        for entity in entities
        if entity.entity_type == HERO_ENTITY_TYPES[entity.name]
    }
    if entity_ids.keys() != HERO_ENTITY_TYPES.keys():
        return False

    documents = session.query(Document).all()
    document_ids: dict[str, set[str]] = {}
    for identity in HERO_DOCUMENT_IDENTITIES:
        matches = {
            document.id
            for document in documents
            if all(getattr(document, field) == expected for field, expected in identity.items())
        }
        if not matches:
            return False
        document_ids[identity["title"]] = matches

    passages = session.query(Passage).all()
    passage_ids: dict[tuple[str, str], set[str]] = {}
    for document_title, text in HERO_PASSAGE_ASSOCIATIONS:
        matches = {
            passage.id
            for passage in passages
            if passage.document_id in document_ids[document_title] and passage.text == text
        }
        if not matches:
            return False
        passage_ids[(document_title, text)] = matches

    edges = session.query(Edge).all()
    for signature in HERO_EDGE_SIGNATURES:
        (
            source,
            target,
            relationship,
            metric,
            value,
            unit,
            period,
            evidence,
            status,
            document_title,
            passage_text,
            verification,
        ) = signature
        expected_document_ids = document_ids[document_title] if document_title else {None}
        expected_passage_ids = (
            passage_ids[(document_title, passage_text)] if passage_text else {None}
        )
        if not any(
            edge.source_entity_id == entity_ids[source]
            and edge.target_entity_id == entity_ids[target]
            and edge.relationship_type == relationship
            and edge.metric == metric
            and edge.value == value
            and edge.unit == unit
            and edge.period == period
            and edge.evidence_class == evidence
            and edge.status == status
            and edge.document_id in expected_document_ids
            and edge.passage_id in expected_passage_ids
            and edge.verification == verification
            for edge in edges
        ):
            return False

    return True


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
    # The approved deployment runs one uvicorn process; cross-process locking is out of scope.
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
