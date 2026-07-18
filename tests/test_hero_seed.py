from fragility_map.model.evidence import StructureType
from fragility_map.seed.hero import hero_companies, hero_relationships, hero_shock


def test_hero_seed_has_three_accessioned_structural_edges() -> None:
    relationships = hero_relationships()

    assert {relationship.relationship_id for relationship in relationships} == {
        "openai-msft",
        "openai-coreweave",
        "coreweave-nvda",
    }
    assert all(relationship.source_accession for relationship in relationships)
    assert (
        next(r for r in relationships if r.relationship_id == "openai-msft").ownership_share
        == 0.27
    )
    assert (
        next(
            r for r in relationships if r.relationship_id == "openai-coreweave"
        ).committed_envelope
        == 11_900_000_000
    )
    assert (
        next(r for r in relationships if r.relationship_id == "coreweave-nvda").structure_type
        is StructureType.BEHAVIOURAL
    )


def test_hero_shock_has_explicit_observed_states() -> None:
    shock = hero_shock()

    assert (
        shock.source_company_id,
        shock.incremental_gaap_loss,
        shock.credit_status,
        shock.default_status,
    ) == ("openai", 10_000_000_000, "severe_distress", "not_defaulted")
    assert set(hero_companies()) >= {"openai", "msft", "coreweave", "nvda"}


def test_every_numeric_hero_relationship_has_immutable_primary_evidence() -> None:
    numeric_relationships = [
        relationship
        for relationship in hero_relationships()
        if relationship.ownership_share is not None
        or relationship.concentration is not None
        or relationship.committed_envelope is not None
    ]

    assert {relationship.relationship_id for relationship in numeric_relationships} == {
        "openai-msft",
        "openai-coreweave",
    }
    assert all(relationship.source_accession for relationship in numeric_relationships)
    assert all(relationship.evidence_quote for relationship in numeric_relationships)
    assert all(relationship.source_location for relationship in numeric_relationships)
