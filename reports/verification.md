# Expected versus observed

Generated without provider calls.

Semantic checks are coding-assistant source inspection, not automatic entailment or human approval.

| Question | Strategy | State | Required citations | Source inspection | Result |
| --- | --- | --- | --- | --- | --- |
| Q1 | retrieval | supported | True | True | PASS |
| Q2 | retrieval | unknown | True | True | PASS |
| Q3 | retrieval | supported | True | True | PASS |
| Q4 | retrieval | supported | True | True | PASS |
| Q5 | retrieval | supported | True | True | PASS |
| Q6 | retrieval | supported | True | True | PASS |
| Q7 | retrieval | supported | True | True | PASS |
| Q8 | retrieval | supported | True | True | PASS |
| Q9 | retrieval | supported | True | True | PASS |
| Q1 | full_context | supported | True | True | PASS |
| Q2 | full_context | unknown | True | True | PASS |
| Q3 | full_context | supported | True | True | PASS |
| Q4 | full_context | supported | True | True | PASS |
| Q5 | full_context | supported | True | True | PASS |
| Q6 | full_context | supported | True | True | PASS |
| Q7 | full_context | supported | True | True | PASS |
| Q8 | full_context | supported | True | True | PASS |
| Q9 | full_context | supported | True | True | PASS |

## Required demonstrations

- supported-citations: PASS — Q3 is supported with its existing support passage
- unknown-route: PASS — Q2 remains unknown and routes to Product reviewer
- explicit-replacement: PASS — Q1 cites the explicit replacement and preserves historical disagreement
- approved-correction-reuse: PASS — No. Only paid-plan users can export CSV; free-plan users cannot.
- restart-and-version-invalidation: PASS — Approval survives restart; referenced version change blocks reuse

## Limits

- Nine examples do not prove general accuracy or latency.
- Source inspection is AI-assisted; actual approval requires human review.
- Provider caching and request timing confound latency comparisons.
- Workflow approval acknowledgements below are scripted simulations.
