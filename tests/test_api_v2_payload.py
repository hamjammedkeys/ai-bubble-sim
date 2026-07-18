from fragility_map.api.v2_payload import build_evidence_payload
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import Shock, StructuralRelationship, run_compound_shock


def _reported() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.CONSTRAINED,
    )


def test_payload_keeps_impact_and_exposure_separate() -> None:
    relationships = [
        StructuralRelationship(
            "openai-msft",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _reported(),
            ownership_share=0.27,
            source_accession="openai-10k-2025",
        ),
        StructuralRelationship(
            "openai-coreweave",
            "openai",
            "coreweave",
            StructureType.TAKE_OR_PAY,
            _reported(),
            committed_envelope=11_900_000_000,
            source_accession="coreweave-s1a-2025",
        ),
    ]
    shock = Shock(
        "openai", incremental_gaap_loss=10_000_000_000, credit_status="severe_distress"
    )

    payload = build_evidence_payload(
        {}, relationships, run_compound_shock(relationships, shock)
    )

    msft = next(node for node in payload["nodes"] if node["companyId"] == "msft")
    coreweave = next(
        node for node in payload["nodes"] if node["companyId"] == "coreweave"
    )
    assert msft["quantifiedImpact"] == -2_700_000_000
    assert msft["rankingEligible"] is True
    assert coreweave["activatedExposure"] == 11_900_000_000
    assert coreweave["quantifiedImpact"] is None
    assert coreweave["rankingEligible"] is False
    assert all(edge["resultKind"] != "realized_loss" for edge in payload["edges"])
    assert payload["scenario"] == {
        "incrementalGaapLoss": 10_000_000_000,
        "creditStatus": "severe_distress",
        "defaultStatus": "not_defaulted",
        "language": "calculated Impact plus activated Exposure; downstream loss not identifiable",
    }
    assert payload["reviewCandidates"] == []
    assert payload["auditLog"] == []
    assert payload["ranking"] == [{"companyId": "msft", "magnitude": 2_700_000_000}]


def test_payload_serializes_edge_evidence_with_stable_camel_case_names() -> None:
    relationship = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _reported(),
        ownership_share=0.27,
        source_accession="openai-10k-2025",
    )

    payload = build_evidence_payload(
        {},
        [relationship],
        run_compound_shock([relationship], Shock("openai", incremental_gaap_loss=100)),
    )

    assert payload["edges"] == [
        {
            "relationshipId": "openai-msft",
            "source": "openai",
            "target": "msft",
            "structureType": "equity_method",
            "tier": "solid_red",
            "resultKind": "impact",
            "value": -27.0,
            "basis": "equity-method share of stated GAAP loss",
            "provenance": {
                "relationship": "reported",
                "magnitude": "reported",
                "propagation": "calculated",
                "timing": "constrained_estimate",
            },
            "sourceAccession": "openai-10k-2025",
        }
    ]


def test_payload_marks_unidentifiable_nodes_ineligible_for_ranking() -> None:
    relationship = StructuralRelationship(
        "coreweave-nvda",
        "coreweave",
        "nvda",
        StructureType.BEHAVIOURAL,
        _reported(),
    )

    payload = build_evidence_payload(
        {},
        [relationship],
        run_compound_shock(
            [relationship], Shock("coreweave", credit_status="severe_distress")
        ),
    )

    node = next(node for node in payload["nodes"] if node["companyId"] == "nvda")
    assert node["epistemicState"] == "not_identifiable"
    assert node["rankingEligible"] is False
    assert payload["ranking"] == []
