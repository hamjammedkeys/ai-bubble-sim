"""Seed the hero graph from figures verified against primary SEC filings.

Every "solid" number and its citation here is verbatim-confirmed in the filing named
on the edge's document — see `revamp/docs/research/2026-07-19-headline-figures-verification.md`
for the full source trail (filing, accession, URL, quoted sentence). Run:

    uv run python seed_hero.py

Verified figures used below:
- Microsoft ~27% as-converted OpenAI ownership, equity method (MSFT 10-Q, quarter ended
  2026-03-31). Post-Oct-2025 recapitalization only — carries a date qualifier, not timeless.
- OpenAI's ~$11.9B commitment to CoreWeave through October 2030 (CoreWeave S-1/A, 2025-03-20),
  still current in CoreWeave's Q1-2026 10-Q.
- A SECOND, newer OpenAI→CoreWeave commitment of ~$6.5B through May 2031 (CoreWeave Q1-2026
  10-Q) — seeded as a candidate awaiting review.
- The same S-1/A also contains an UNRELATED $11.9B (data-center leases) — seeded as a flagged
  candidate so the review queue shows the verifier catching a same-filing false-positive.
"""

from datetime import date

from app.db import Base, SessionLocal, engine
from app.models import Document, Edge, Entity, Passage


def _reset() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed() -> None:
    _reset()
    s = SessionLocal()

    def entity(name: str, entity_type: str) -> Entity:
        e = Entity(name=name, entity_type=entity_type, aliases=[])
        s.add(e)
        s.flush()
        return e

    # Layered economy: investor -> model -> cloud -> gpu -> foundry -> equipment
    msft = entity("Microsoft", "investor")
    openai = entity("OpenAI", "model_company")
    coreweave = entity("CoreWeave", "cloud_provider")
    nvidia = entity("Nvidia", "gpu_maker")
    tsmc = entity("TSMC", "foundry")
    asml = entity("ASML", "equipment_maker")

    def document(**kw) -> Document:
        d = Document(**kw)
        s.add(d)
        s.flush()
        return d

    # --- Primary-source documents (real filings) ---
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
        p = Passage(document_id=doc.id, text=text)
        s.add(p)
        s.flush()
        return p.id

    def edge(src, tgt, rel, *, metric=None, value=None, unit=None, period=None,
             evidence_class, status="approved", doc=None, passage_id=None, verification=None):
        s.add(Edge(
            source_entity_id=src.id, target_entity_id=tgt.id, relationship_type=rel,
            metric=metric, value=value, unit=unit, period=period, evidence_class=evidence_class,
            passage_id=passage_id, document_id=doc.id if doc else None, status=status,
            verification=verification,
        ))

    _pass = {"overall": "pass", "passage_found": True, "match_score": 100, "number_found": True}

    # --- Solid quantified core (approved, primary-sourced) ---
    edge(
        msft, openai, "equity_method", metric="ownership_pct", value=27.0, unit="percent",
        period="as-converted, as of Mar 31, 2026 (post Oct-2025 recap)", evidence_class="reported",
        doc=doc_msft,
        passage_id=passage(doc_msft, "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting."),
        verification=_pass,
    )
    edge(
        openai, coreweave, "purchase_obligation", metric="contract_value", value=11.9,
        unit="usd_billions", period="through October 2030", evidence_class="reported",
        doc=doc_cw_s1a,
        passage_id=passage(doc_cw_s1a, "OpenAI has committed to pay us up to approximately $11.9 billion through October 2030."),
        verification=_pass,
    )

    # --- Amber behavioural periphery (documented industry structure, never quantified) ---
    for a, b in [(coreweave, nvidia), (nvidia, tsmc), (tsmc, asml)]:
        edge(a, b, "supplier_dependency", evidence_class="unknown")

    # --- Candidate awaiting review: a REAL second OpenAI->CoreWeave commitment (approve example) ---
    edge(
        openai, coreweave, "purchase_obligation", metric="contract_value", value=6.5,
        unit="usd_billions", period="through May 2031", evidence_class="reported",
        status="candidate", doc=doc_cw_10q,
        passage_id=passage(doc_cw_10q, "OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031."),
        verification=_pass,
    )
    # --- Candidate that SHOULD be rejected: the same S-1/A's unrelated $11.9B data-center
    #     lease, mis-extracted as an OpenAI purchase obligation. The cited passage never
    #     mentions OpenAI, so the mechanical entity check flags it (overreach). ---
    edge(
        openai, coreweave, "purchase_obligation", metric="contract_value", value=11.9,
        unit="usd_billions", period="lease term", evidence_class="reported",
        status="candidate", doc=doc_cw_s1a,
        passage_id=passage(doc_cw_s1a, "The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion."),
        verification={"overall": "flag", "passage_found": True, "match_score": 100,
                      "number_found": True, "entities_found": False,
                      "note": "passage describes data-center leases, not an OpenAI commitment"},
    )

    from app.models import Scenario

    s.add(Scenario(
        name="OpenAI credit event",
        description="OpenAI reports a +$10B incremental GAAP loss under severe distress.",
        shock_json={"origin_entity": "OpenAI", "kind": "gaap_loss", "magnitude": 10.0, "unit": "usd_billions"},
    ))

    s.commit()
    counts = {
        "entities": s.query(Entity).count(),
        "approved_edges": s.query(Edge).filter(Edge.status == "approved").count(),
        "candidate_edges": s.query(Edge).filter(Edge.status == "candidate").count(),
        "documents": s.query(Document).count(),
    }
    s.close()
    print("seeded:", counts)


if __name__ == "__main__":
    seed()
