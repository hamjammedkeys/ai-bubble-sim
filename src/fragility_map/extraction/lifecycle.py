from dataclasses import dataclass

from fragility_map.extraction.candidates import CandidateStatus, RelationshipCandidateV2
from fragility_map.extraction.verifier import VerificationResult
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import StructuralRelationship


@dataclass(frozen=True)
class AuditEvent:
    candidate_id: str
    from_status: CandidateStatus | None
    to_status: CandidateStatus
    reviewer_id: str
    reason: str
    verification_valid: bool


class CandidateLifecycle:
    def __init__(self) -> None:
        self._items: dict[str, tuple[RelationshipCandidateV2, VerificationResult]] = {}
        self._audit: list[AuditEvent] = []

    def submit(self, candidate: RelationshipCandidateV2, verification: VerificationResult) -> None:
        if candidate.status is not CandidateStatus.PROPOSED:
            raise ValueError("candidate must start proposed")
        self._items[candidate.candidate_id] = (candidate, verification)

    def _get(self, candidate_id: str) -> tuple[RelationshipCandidateV2, VerificationResult]:
        try:
            return self._items[candidate_id]
        except KeyError as error:
            raise KeyError(f"unknown candidate: {candidate_id}") from error

    @staticmethod
    def _require_reviewer(reviewer_id: str, reason: str) -> None:
        if not reviewer_id.strip() or not reason.strip():
            raise ValueError("reviewer_id and reason are required")

    def approve(self, candidate_id: str, reviewer_id: str, reason: str) -> RelationshipCandidateV2:
        self._require_reviewer(reviewer_id, reason)
        candidate, verification = self._get(candidate_id)
        if not verification.mechanically_valid:
            raise ValueError("candidate failed mechanical verification")
        if candidate.status in {
            CandidateStatus.REJECTED,
            CandidateStatus.APPROVED,
            CandidateStatus.EDITED,
        }:
            raise ValueError("candidate cannot be approved from its current state")
        updated = candidate.model_copy(update={"status": CandidateStatus.APPROVED})
        self._items[candidate_id] = (updated, verification)
        self._audit.append(
            AuditEvent(candidate_id, candidate.status, updated.status, reviewer_id, reason, True)
        )
        return updated

    def edit(
        self,
        candidate_id: str,
        edited_candidate: RelationshipCandidateV2,
        reviewer_id: str,
        reason: str,
        verification: VerificationResult,
    ) -> RelationshipCandidateV2:
        self._require_reviewer(reviewer_id, reason)
        candidate, _ = self._get(candidate_id)
        if (
            candidate.status is CandidateStatus.REJECTED
            or edited_candidate.candidate_id != candidate_id
        ):
            raise ValueError("candidate cannot be edited")
        updated = edited_candidate.model_copy(update={"status": CandidateStatus.EDITED})
        self._items[candidate_id] = (updated, verification)
        self._audit.append(
            AuditEvent(
                candidate_id,
                candidate.status,
                updated.status,
                reviewer_id,
                reason,
                verification.mechanically_valid,
            )
        )
        return updated

    def reject(self, candidate_id: str, reviewer_id: str, reason: str) -> RelationshipCandidateV2:
        self._require_reviewer(reviewer_id, reason)
        candidate, verification = self._get(candidate_id)
        if candidate.status is CandidateStatus.REJECTED:
            raise ValueError("candidate already rejected")
        updated = candidate.model_copy(update={"status": CandidateStatus.REJECTED})
        self._items[candidate_id] = (updated, verification)
        self._audit.append(
            AuditEvent(
                candidate_id,
                candidate.status,
                updated.status,
                reviewer_id,
                reason,
                verification.mechanically_valid,
            )
        )
        return updated

    def get(self, candidate_id: str) -> RelationshipCandidateV2:
        return self._get(candidate_id)[0]

    def audit_log(self) -> tuple[AuditEvent, ...]:
        return tuple(self._audit)


def promote_approved(
    candidate: RelationshipCandidateV2, verification: VerificationResult
) -> StructuralRelationship:
    if candidate.status not in {CandidateStatus.APPROVED, CandidateStatus.EDITED}:
        raise ValueError("only approved candidates may be promoted")
    if not verification.mechanically_valid:
        raise ValueError("candidate failed mechanical verification")
    try:
        structure_type = StructureType(candidate.relationship_type)
    except ValueError as error:
        raise ValueError(f"unsupported relationship type: {candidate.relationship_type}") from error
    if candidate.value is None and structure_type in {
        StructureType.TAKE_OR_PAY,
        StructureType.CUSTOMER_CONCENTRATION,
    }:
        raise ValueError("typed value required for promotion")
    provenance = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.CONSTRAINED,
    )
    return StructuralRelationship(
        candidate.candidate_id,
        candidate.source_company_id,
        candidate.target_company_id or "unknown_target",
        structure_type,
        provenance,
        concentration=candidate.value
        if structure_type is StructureType.CUSTOMER_CONCENTRATION
        else None,
        committed_envelope=candidate.value if structure_type is StructureType.TAKE_OR_PAY else None,
        source_accession=candidate.source_accession,
    )
