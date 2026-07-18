# Task 4 Report: Take-or-pay Exposure

## Status

DONE

## Implementation

- Extended `run_compound_shock` with a `TAKE_OR_PAY` branch.
- Activates only when credit status is `severe_distress` or default status is `defaulted`, and provenance permits quantified propagation.
- Emits a `SOLID_ORANGE` edge with `result_kind="exposure"`, the committed envelope as its value, and the required not-a-realized-loss basis.
- Accumulates same-target activated exposure without adding it to quantified impact.
- Preserves an existing quantified impact and keeps `epistemic_state="quantified_impact"`; otherwise marks the node `exposure_detected`.
- Leaves non-distressed take-or-pay relationships dormant.

## Files changed

- `src/fragility_map/model/propagation.py`
- `tests/test_stress_model.py`

## TDD evidence

### RED

Command:

```text
pytest tests/test_stress_model.py::test_take_or_pay_produces_solid_orange_exposure_not_loss -v
```

Result: exit 1, one failed test. Expected failure:

```text
E       IndexError: list index out of range
FAILED tests/test_stress_model.py::test_take_or_pay_produces_solid_orange_exposure_not_loss
============================== 1 failed in 0.14s ===============================
```

### GREEN

Focused command:

```text
pytest tests/test_stress_model.py::test_take_or_pay_produces_solid_orange_exposure_not_loss -v
```

Result:

```text
PASSED
============================== 1 passed in 0.06s ===============================
```

Full requested test command:

```text
pytest tests/test_stress_model.py -v
```

Result:

```text
============================== 11 passed in 0.06s ==============================
```

## Lint

Command:

```text
make lint
```

Result:

```text
ruff check src tests
All checks passed!
```

`git diff --check` also exited 0 with no output.

## Additional verification

An ad-hoc mixed same-target check covered one equity impact followed by two take-or-pay exposures under default distress. It confirmed quantified impact `-100.0`, accumulated activated exposure `150`, epistemic state `quantified_impact`, and edge kinds `impact`, `exposure`, `exposure`.

## Self-review

- Tests from the brief were appended unchanged.
- No legacy tests or unrelated files were modified.
- Exposure never enters `quantified_impact`.
- Both distress signals activate the branch.
- Existing exposure accumulates and existing impact is preserved regardless of relationship ordering already supported by the equity branch.
- The implementation is confined to the existing loop and follows the established result construction style.

## Concerns

The original review noted that `committed_envelope` remained nullable. The follow-up below verifies and fixes that case by suppressing propagation when the disclosed envelope is absent.

## Important-review follow-up

### Automated coverage added

- `test_take_or_pay_activates_on_default_and_uses_required_basis`: verifies `default_status="defaulted"` activation and the exact required edge basis.
- `test_take_or_pay_accumulates_while_preserving_quantified_impact`: uses the existing engine with an equity relationship followed by two same-target take-or-pay relationships; verifies exposure accumulation, preserved quantified impact, and `epistemic_state="quantified_impact"`.
- `test_take_or_pay_rejects_non_quantifying_or_missing_envelope`: verifies both non-quantifying provenance and a missing committed envelope produce no edge, node, or fabricated numeric value.

### Pre-production-change characterization / RED

Command:

```text
pytest tests/test_stress_model.py::test_take_or_pay_activates_on_default_and_uses_required_basis tests/test_stress_model.py::test_take_or_pay_accumulates_while_preserving_quantified_impact tests/test_stress_model.py::test_take_or_pay_rejects_non_quantifying_or_missing_envelope -v
```

Result: exit 1; default activation/basis and accumulation/preservation passed, while the rejection test failed because the missing-envelope relationship emitted one exposure edge with `value=None`. This was the only real production defect exposed; no artificial RED was created for already-correct behavior.

### Production fix

Added a minimal `rel.committed_envelope is None` guard to the take-or-pay activation branch so absent contract magnitude cannot emit a numeric exposure result.

### GREEN and full verification

- `pytest tests/test_stress_model.py::test_take_or_pay_rejects_non_quantifying_or_missing_envelope -v` — 1 passed, exit 0.
- `pytest tests/test_stress_model.py -v` — 14 passed, exit 0.
- `make lint` — `ruff check src tests`; all checks passed, exit 0.
- `git diff --check` — exit 0, no output.

### Files

- `src/fragility_map/model/propagation.py`
- `tests/test_stress_model.py`
- `.superpowers/sdd/task-4-report.md`

### Follow-up self-review

- Coverage is consolidated into three focused tests while explicitly checking all requested findings.
- The production change is limited to rejecting an absent disclosed envelope; existing distress, provenance, accumulation, impact-preservation, and epistemic-state logic is unchanged.
- Exposure remains separate from quantified impact and no zero or other invented fallback is introduced.

### Follow-up concerns

None.

### Follow-up commit

`00db281 fix(engine): reject unquantified take-or-pay exposure`
