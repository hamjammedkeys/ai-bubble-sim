import json
from math import isfinite
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fragility_map.api.v2_payload import build_evidence_payload
from fragility_map.db.repository import FragilityRepository
from fragility_map.extraction.candidates import CandidateStatus, RelationshipCandidateV2
from fragility_map.extraction.lifecycle import CandidateLifecycle
from fragility_map.extraction.verifier import (
    SourceManifestEntry,
    VerificationCheck,
    VerificationResult,
    verify_candidate,
)
from fragility_map.model.graph_export import build_graph_payload
from fragility_map.model.propagation import Shock, ShockResult, run_compound_shock
from fragility_map.model.stress import (
    CompanyFinancials,
    NetworkRelationship,
    ScenarioConfig,
    run_cloud_spending_slowdown,
)
from fragility_map.seed.hero import hero_companies, hero_relationships, hero_shock
from fragility_map.settings import get_paths

app = FastAPI(title="AI Fragility Map API")


class ScenarioRequest(BaseModel):
    shock_percentage: float = Field(default=0.30, ge=0.0, le=1.0)
    pass_through_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    propagation_factor: float = Field(default=0.50, ge=0.0, le=1.0)
    max_rounds: int = Field(default=3, ge=1, le=3)


class CompoundCreditEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    incremental_gaap_loss: float = Field(ge=0.0)
    credit_status: Literal["normal", "severe_distress"]
    default_status: Literal["not_defaulted", "defaulted"]

    @field_validator("incremental_gaap_loss", mode="before")
    @classmethod
    def reject_nonfinite_loss(cls, value: Any) -> Any:
        if isinstance(value, float) and not isfinite(value):
            return "non-finite"
        if isinstance(value, str) and value.strip().lower() in {
            "nan",
            "inf",
            "+inf",
            "-inf",
            "infinity",
            "+infinity",
            "-infinity",
        }:
            return "non-finite"
        return value


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @field_validator("reviewer_id", "reason")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ReviewEditRequest(ReviewDecisionRequest):
    candidate: RelationshipCandidateV2

    @model_validator(mode="before")
    @classmethod
    def reject_client_result_fields(cls, value: Any) -> Any:
        candidate = value.get("candidate", {}) if isinstance(value, dict) else {}
        if isinstance(candidate, dict):
            unexpected_fields = candidate.keys() - RelationshipCandidateV2.model_fields.keys()
            if unexpected_fields:
                raise ValueError("clients cannot provide a result or tier")
        return value


def demo_companies() -> dict[str, CompanyFinancials]:
    return {
        "msft": CompanyFinancials(
            "msft", "Microsoft", "cloud_platform", 245_000, 75_000, 97_000, 110_000, 2_000
        ),
        "amzn": CompanyFinancials(
            "amzn", "Amazon", "cloud_platform", 638_000, 89_000, 135_000, 68_000, 3_000
        ),
        "googl": CompanyFinancials(
            "googl", "Alphabet", "cloud_platform", 350_000, 110_000, 30_000, 115_000, 1_000
        ),
        "meta": CompanyFinancials(
            "meta", "Meta Platforms", "cloud_platform", 164_000, 70_000, 37_000, 70_000, 500
        ),
        "orcl": CompanyFinancials(
            "orcl", "Oracle", "cloud_platform", 53_000, 11_000, 88_000, 18_000, 4_000
        ),
        "nvda": CompanyFinancials(
            "nvda", "NVIDIA", "semiconductor", 130_000, 43_000, 11_000, 81_000, 250
        ),
        "amd": CompanyFinancials(
            "amd", "AMD", "semiconductor", 26_000, 6_000, 3_000, 1_900, 120
        ),
        "smci": CompanyFinancials(
            "smci", "Supermicro", "infrastructure", 15_000, 2_000, 2_000, 1_200, 80
        ),
        "anet": CompanyFinancials(
            "anet", "Arista Networks", "infrastructure", 7_000, 6_000, 0, 2_800, 0
        ),
        "vrt": CompanyFinancials(
            "vrt", "Vertiv", "infrastructure", 8_000, 800, 3_000, 1_000, 250
        ),
        "asml": CompanyFinancials(
            "asml", "ASML", "semiconductor_equipment", 30_000, 7_000, 5_000, 9_000, 100
        ),
        "amat": CompanyFinancials(
            "amat",
            "Applied Materials",
            "semiconductor_equipment",
            27_000,
            8_000,
            6_000,
            8_000,
            250,
        ),
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
    scenario = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.30, 0.80, 0.50, 3),
    )
    return build_graph_payload(companies, relationships, scenario)


@app.post("/api/scenario/cloud-slowdown")
def run_scenario(request: ScenarioRequest) -> dict:
    companies = demo_companies()
    relationships = demo_relationships()
    scenario = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(
            request.shock_percentage,
            request.pass_through_rate,
            request.propagation_factor,
            request.max_rounds,
        ),
    )
    return build_graph_payload(companies, relationships, scenario)


def _compound_result(shock: Shock) -> ShockResult:
    """Run the hero's direct results and its documented behavioural downstream link."""
    relationships = hero_relationships()
    direct_result = run_compound_shock(relationships, shock)
    downstream_result = run_compound_shock(
        relationships,
        Shock("coreweave", credit_status=shock.credit_status, default_status=shock.default_status),
    )
    result = ShockResult(
        edges=[*direct_result.edges, *downstream_result.edges],
        nodes={**direct_result.nodes, **downstream_result.nodes},
        shock=shock,
    )
    return result


def _v2_payload(
    shock: Shock,
    candidates: tuple[RelationshipCandidateV2, ...] = (),
    verifications: tuple[VerificationResult, ...] = (),
    audit_entries: tuple[dict[str, Any], ...] = (),
) -> dict[str, object]:
    payload = build_evidence_payload(
        hero_companies(), hero_relationships(), _compound_result(shock), candidates
    )
    review_candidates = payload["reviewCandidates"]
    assert isinstance(review_candidates, list)
    for candidate_payload, verification in zip(review_candidates, verifications, strict=True):
        candidate_payload["verificationChecks"] = [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in verification.checks
        ]
        candidate_payload["mechanicallyValid"] = verification.mechanically_valid
    payload["auditLog"] = [
        {
            "auditId": entry["audit_id"],
            "candidateId": entry["candidate_id"],
            "fromStatus": entry["from_status"],
            "toStatus": entry["to_status"],
            "reviewerId": entry["reviewer_id"],
            "reason": entry["reason"],
            "verificationValid": entry["verification_valid"],
            "createdAt": entry["created_at"],
        }
        for entry in audit_entries
    ]
    return payload


def _review_repository() -> FragilityRepository:
    repository = getattr(app.state, "review_repository", None)
    if repository is None:
        repository = FragilityRepository(get_paths().db_path)
        repository.create_schema()
        app.state.review_repository = repository
    return repository


def _review_lifecycle() -> CandidateLifecycle:
    lifecycle = getattr(app.state, "review_lifecycle", None)
    if lifecycle is None:
        lifecycle = CandidateLifecycle()
        app.state.review_lifecycle = lifecycle
    return lifecycle


def _verification_from_record(record: dict[str, Any]) -> VerificationResult:
    verification = record["verification"]
    return VerificationResult(
        candidate_id=verification["candidate_id"],
        checks=tuple(VerificationCheck(**check) for check in verification["checks"]),
        semantic_interpretation=verification["semantic_interpretation"],
        mechanically_valid=verification["mechanically_valid"],
    )


def _stored_review_records(
    repository: FragilityRepository,
) -> list[tuple[RelationshipCandidateV2, VerificationResult]]:
    with repository.connect() as connection:
        rows = connection.execute(
            """
            SELECT candidate_json, verification_json
            FROM relationship_candidates
            ORDER BY saved_at, candidate_id
            """
        ).fetchall()
    records: list[tuple[RelationshipCandidateV2, VerificationResult]] = []
    for candidate_json, verification_json in rows:
        record = {
            "candidate": json.loads(candidate_json),
            "verification": json.loads(verification_json),
        }
        records.append(
            (
                RelationshipCandidateV2.model_validate(record["candidate"]),
                _verification_from_record(record),
            )
        )
    return records


def _restore_lifecycle_candidate(
    lifecycle: CandidateLifecycle,
    candidate: RelationshipCandidateV2,
    verification: VerificationResult,
) -> None:
    try:
        lifecycle.get(candidate.candidate_id)
        return
    except KeyError:
        pass
    proposed = candidate.model_copy(update={"status": CandidateStatus.PROPOSED})
    lifecycle.submit(proposed, verification)
    if candidate.status is CandidateStatus.APPROVED:
        lifecycle.approve(candidate.candidate_id, "restored", "restored review state")
    elif candidate.status is CandidateStatus.EDITED:
        lifecycle.edit(
            candidate.candidate_id,
            candidate,
            "restored",
            "restored review state",
            verification,
        )
    elif candidate.status is CandidateStatus.REJECTED:
        lifecycle.reject(candidate.candidate_id, "restored", "restored review state")


def _stored_filing_text(repository: FragilityRepository, source_id: str) -> str:
    with repository.connect() as connection:
        row = connection.execute(
            "SELECT local_path FROM sources WHERE source_id = ?", [source_id]
        ).fetchone()
    if row is None or row[0] is None:
        raise HTTPException(status_code=409, detail="stored filing text is unavailable")
    source_path = Path(row[0])
    if not source_path.is_file():
        raise HTTPException(status_code=409, detail="stored filing text is unavailable")
    return source_path.read_text(encoding="utf-8")


def _review_payload(repository: FragilityRepository) -> dict[str, object]:
    records = _stored_review_records(repository)
    pending = [
        (candidate, verification)
        for candidate, verification in records
        if candidate.status is CandidateStatus.PROPOSED
    ]
    audit_entries = tuple(
        entry
        for candidate, _ in records
        for entry in repository.list_candidate_audit(candidate.candidate_id)
    )
    return _v2_payload(
        hero_shock(),
        tuple(candidate for candidate, _ in pending),
        tuple(verification for _, verification in pending),
        audit_entries,
    )


def _transition_candidate(
    candidate_id: str,
    reviewer_id: str,
    reason: str,
    action: Literal["approve", "edit", "reject"],
    edited_candidate: RelationshipCandidateV2 | None = None,
) -> dict[str, object]:
    repository = _review_repository()
    record = repository.get_candidate(candidate_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown candidate")
    candidate = RelationshipCandidateV2.model_validate(record["candidate"])
    verification = _verification_from_record(record)
    lifecycle = _review_lifecycle()
    _restore_lifecycle_candidate(lifecycle, candidate, verification)
    if action == "edit" and (
        edited_candidate is None or edited_candidate.candidate_id != candidate_id
    ):
        raise HTTPException(status_code=422, detail="edited candidate ID must match the route")
    try:
        if action == "approve":
            updated = lifecycle.approve(candidate_id, reviewer_id, reason)
        elif action == "reject":
            updated = lifecycle.reject(candidate_id, reviewer_id, reason)
        else:
            assert edited_candidate is not None
            edited_verification = verify_candidate(
                _stored_filing_text(repository, candidate.source_id),
                edited_candidate,
                [
                    SourceManifestEntry(
                        edited_candidate.source_accession, edited_candidate.source_id
                    )
                ],
            )
            updated = lifecycle.edit(
                candidate_id,
                edited_candidate,
                reviewer_id,
                reason,
                edited_verification,
            )
            verification = edited_verification
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    repository.save_candidate(updated, verification)
    repository.record_candidate_audit(lifecycle.audit_log()[-1])
    return _review_payload(repository)


@app.post("/api/v2/scenario/compound-credit-event")
def run_compound_credit_event(request: CompoundCreditEventRequest) -> dict[str, object]:
    return _v2_payload(
        Shock(
            "openai",
            request.incremental_gaap_loss,
            request.credit_status,
            request.default_status,
        )
    )


@app.get("/api/v2/review/candidates")
def get_review_candidates() -> dict[str, object]:
    return _review_payload(_review_repository())


@app.post("/api/v2/review/{candidate_id}/approve")
def approve_review_candidate(
    candidate_id: str, request: ReviewDecisionRequest
) -> dict[str, object]:
    return _transition_candidate(candidate_id, request.reviewer_id, request.reason, "approve")


@app.post("/api/v2/review/{candidate_id}/edit")
def edit_review_candidate(candidate_id: str, request: ReviewEditRequest) -> dict[str, object]:
    return _transition_candidate(
        candidate_id,
        request.reviewer_id,
        request.reason,
        "edit",
        request.candidate,
    )


@app.post("/api/v2/review/{candidate_id}/reject")
def reject_review_candidate(candidate_id: str, request: ReviewDecisionRequest) -> dict[str, object]:
    return _transition_candidate(candidate_id, request.reviewer_id, request.reason, "reject")
