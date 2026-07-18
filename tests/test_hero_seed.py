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
