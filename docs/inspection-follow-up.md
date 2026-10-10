# Independent inspection follow-up

The supplied 10 October 2026 inspection reviewed main commit
`d63f4a3e89ddcdd32d09e0561cde7c20d6ca1705`. Its four reported defects were reproduced
locally before applying fixes. This follow-up is the implementer's verification, not a
second independent review or human semantic approval of model answers.

| Finding | Reproduction | Correction and regression evidence |
| --- | --- | --- |
| Mistaken conflict decision cannot be corrected | Changing only answerability leaves unresolved conflict metadata; approval is blocked and no conflict editor exists. | The form now edits resolution, conflict passages, and explanations into a new revision. AppTest proves unresolved and unrelated-source conflicts remain blocked, then corrects explicit replacement evidence, approves, and reuses exact wording with zero provider calls. Original revisions remain unchanged. |
| Note before generation stays pending | A saved reviewer note leaves status pending and the unresolved count at zero. | A valid unknown draft with the note is saved even before generation. Store restart and UI queue/count regressions verify persistence and that it remains unapprovable. |
| Invalid citation becomes a freshness warning | A nonexistent passage returns an initial error, then becomes needs_review on reload. | Status validates against the immutable original dataset before checking freshness. A fabricated reference stays an error; a valid passage removed by a later import remains needs_review. |
| Malformed provider content crashes generation | HTTP 200 with null message/content blocks raises AttributeError. | The text-only provider envelope is explicitly checked. Sixteen malformed message/content shapes produce a safe error in live simulation and replay; the next question in a batch still completes. |

Local checks after correction: 63 tests passed (21 additional regression cases), Ruff
lint/format checks passed, all 18 selected real recordings passed expectations, and all
five required scripted demonstrations passed. Verification and repairs made zero real API
requests. Provider failure tests use HTTPX MockTransport and temporary recordings only.

No prompt, model configuration, original fixture, approval requirement, or source-authority
rule changed. Cohere Command A remains the main runtime; the Command A+ experiment remains
separate. The original time allowance is not asserted to cover this additional work; see
the work log and handoff for recorded checkpoints and submission provenance.
