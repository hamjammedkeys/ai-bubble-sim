# Task 6 report: edge-flow vs aggregate guardrail

## Result

- Added `run_edge_flow_shock`, which quantifies only the named, eligible
  `CUSTOMER_CONCENTRATION` relationship as a signed, six-decimal exposure.
- Added an aggregate guard before the unconstrained/behavioural dissolve gate, so
  `run_compound_shock` emits no edge or node for concentration relationships.
- Added coverage for signed rounding, aggregate silence for both quantifying and
  unconstrained provenance, relationship-id mismatch, wrong structure, missing
  concentration, and non-quantifying provenance.

## RED

Command:

```text
pytest tests/test_stress_model.py::test_concentration_edge_is_solid_only_under_edge_flow_shock -v
```

Observed exit code: `4`. Collection failed with the expected cause:

```text
ImportError: cannot import name 'run_edge_flow_shock' from
'fragility_map.model.propagation'
```

## GREEN

Command:

```text
pytest tests/test_stress_model.py -v
```

Output:

```text
collected 20 items
20 passed in 0.03s
```

Command:

```text
make lint
```

Output:

```text
ruff check src tests
All checks passed!
```

## Files

- `src/fragility_map/model/propagation.py`
- `tests/test_stress_model.py`
- `.superpowers/sdd/task-6-report.md`

## Self-review and concerns

- The concentration guard is deliberately after source matching but before the
  Task 5 dissolve gate, matching the binding ordering requirement.
- The edge-flow API does not aggregate duplicate relationship IDs; relationship
  IDs are treated as identifiers, and the brief specifies quantifying the one
  relationship named by the shock.
- No legacy pre-plan tests or unrelated modules were changed.
- No outstanding concerns.
