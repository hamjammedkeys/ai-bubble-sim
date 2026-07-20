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

from app.db import Base, SessionLocal, engine
from app.models import Document, Edge, Entity
from app.services.hero_seed import seed_hero_if_empty


def reset_and_seed() -> None:
    """Destructively recreate the local database and insert the hero graph."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as session:
        seed_hero_if_empty(session)

    with SessionLocal() as session:
        counts = {
            "entities": session.query(Entity).count(),
            "approved_edges": session.query(Edge).filter(Edge.status == "approved").count(),
            "candidate_edges": session.query(Edge).filter(Edge.status == "candidate").count(),
            "documents": session.query(Document).count(),
        }
    print("seeded:", counts)


if __name__ == "__main__":
    reset_and_seed()
