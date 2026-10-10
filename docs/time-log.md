# Work log

Implementation began 2026-10-09 at 09:20:52 UTC (12:20:52 Europe/Riga).
Record actual elapsed work, checks, corrections, and unfinished items here.

Prior preparation included assignment discussion, company research, architecture planning,
and checking/moving the supplied Cohere credential out of the environment example.
Its duration was not instrumented; it must not be represented as zero or hidden in the final report.

| Activity | Start UTC | End UTC | Notes |
| --- | --- | --- | --- |
| Instrumented build through verified main checkpoint | 09:20:52 | 14:28:59 | 5 h 8 min 7 s; setup, data, implementation, model calls, verification, Git, and documentation. Final handoff publication follows this checkpoint. |

## Recorded milestones

- Initial reproducible baseline and source/fixture core committed on separate branches.
- PR #1 passed CI and was merged; repository privacy verified.
- Primary Cohere integration: nine questions recorded under retrieval and full context.
- Eight real capture/preflight failures retained; no malformed output substituted for success.
- 18 selected recordings independently source-inspected by the coding assistant.
- Five required scripted demonstrations passed with zero new provider calls.
- PR #2 passed CI and was merged. Alternate Command A+ pilot committed separately in draft PR #3.
- Local interface inspected and 42 tests passed, including keyless UI review/edit/reuse.
- At 13:58:07 UTC, instrumented wall-clock work was 4 hours 37 minutes. Container and delivery
  checks were still pending. Completion time will be recorded after those checks.
- PR #4's first container run built the image and passed replay, but an early health probe
  encountered a connection reset. Bounded readiness retries were corrected before merging.
- PR #4 passed validation and actual container recreation checks after the fix and was merged.
- Main run 37943987430 passed validation, container checks, and delivery; the extracted source
  package also passed all 18 replay cases and five scripted demonstrations locally with zero API calls.
- 35 real provider attempts were made in the shared local database: 34 implementation/preflight
  attempts plus the separately requested Command A+ pilot. Eight failures remain documented.
- Implementation and initial main delivery were complete at 14:28:59 UTC (17:28:59 Europe/Riga).
  The final documentation PR and CI publication add a few minutes; their timestamps remain
  available in Git and GitHub Actions. No history or laptop clock was altered.

These are measured/observed milestones, not the earlier estimated allocation. Earlier
preparatory research was not timed; the full exercise total therefore cannot honestly be
represented as exactly eight hours or less solely from this build log.

## User-requested launcher addition after v0.1.0

Added `full_run.sh` on a separate feature branch. It bootstraps pinned uv/Python into the
project, creates the venv, installs the lockfile, runs lint/tests/keyless verification, and
starts the app. A clean source copy without credentials, venv, or local uv completed setup
and all 42 tests plus 18 replay cases. Existing review state and environment credentials
are preserved. CI additionally tests clean Linux bootstrap and package startup.
The extracted package exposed a missing lint exclusion: without Git metadata, Ruff scanned
downloaded dependencies under `.runtime`. Explicit exclusions were added and verified outside
the repository; no vendor files were reformatted or modified.

## Reconstructed later publication interval

Git and GitHub Actions supply dated endpoints for the work after the original measured
checkpoint. These are elapsed wall-clock spans, including possible idle time and CI waits;
they do not establish continuously active engineering hours.

| Activity | Start UTC | End UTC | Elapsed and evidence |
| --- | --- | --- | --- |
| Final documentation, launcher, archive fix, and passing main delivery | 2026-10-09 14:28:59 | 2026-10-09 15:29:51 | 1 h 0 min 52 s from the recorded checkpoint to successful run 37951938687 on d63f4a3. Commits bef0b49, dbe7592, and 37c844a and their merges occurred within this interval. |

The known 9 October implementation/publication window is therefore 09:20:52–15:29:51 UTC,
6 h 8 min 59 s elapsed. Untimed earlier preparation remains additional and unknown.
This is not evidence that the complete exercise consumed eight hours or less.

## Additional inspection follow-up on 10 October

The first recorded timestamp for this follow-up was 05:48:43 UTC; initial report reading
before that timestamp was not separately timed. The endpoint below is an actual observed
checkpoint, not an estimate or a reconstructed start time.

| Activity | Start UTC | End UTC | Elapsed and evidence |
| --- | --- | --- | --- |
| Reproductions, four fixes, regression verification, PR #8, main delivery, and handoff preparation | 2026-10-10 05:48:43 | 2026-10-10 05:58:00 | 9 min 17 s observed wall-clock span. Main b0ddccf passed all four jobs in run 38029175559 at 05:57:33 UTC. Documentation publication follows this checkpoint. |

All four findings were reproduced before correction. The final local check at this point
passed 63 tests, 18 recorded-response cases, and all five required demonstrations, with
zero new real provider calls. Sixteen provider-envelope regressions use simulated HTTP
responses; scripted approval acknowledgements remain simulations, not human peer reviews.
The isolated browser check loaded the saved Q1 response and displayed the conflict editor;
AppTest verified the full correction/approval/reuse interactions. The disposable server
was stopped and the existing local review database was not changed.

A formatting issue introduced by the last test edit was corrected in a separate commit
before opening PR #8. CI passed at its reviewed head before merge. No commit timestamps
or laptop clock were changed. The final handoff commit and its publishing CI run add
time after 05:58:00; their actual endpoints are available in Git/Actions and the delivered
manifest links the producing run. Those later minutes are not included in the 9 min 17 s.

These fixes and publication are additional work after independent inspection. Neither
the uninstrumented intervals nor this follow-up is hidden inside the original eight-hour
allowance. The full exercise total remains unestablished.

## Candidate-requested submission documentation

On 10 October, the candidate requested an inventory of the seven submission deliverables
and an LLM usage note naming additional planning/research tools. The observed interval
06:08:52–06:12:46 UTC was 3 min 54 s through local documentation checks. Added a submission
map and a dedicated usage note, indexed it in the AI configuration, and marked unrecorded
external model/tool versions explicitly. Codex implementation is credited separately from
the candidate-reported Claude Code, Perplexity, and Gemini planning/research roles.

Local checks verified completed manifest references, preserved supplied seeds, nine expected
question cases, and the five original reference cases. Ruff lint/format and diff checks passed.
No real provider requests were made. PR/CI publication follows this measured checkpoint;
its endpoints are available in Git/Actions and the final package manifest. This is additional
submission work, not a revision of the original measured build interval.

## Public submission access

On 10 October, the candidate explicitly confirmed public repository access. Before the
visibility change, Gitleaks scanned all refs without finding leaks, and a separate check
found the current model credential absent from reachable Git objects. GitHub reported
public visibility after the change; anonymous access to `docs/llm-usage.md` returned HTTP 200.

The observed documentation interval 06:30:07–06:30:51 UTC was 44 seconds through local
checks, updating the README and handoff for public access. The visibility change preceded
the first timestamp in this interval. Earlier permission checks and confirmation waiting
are not represented as continuously active work. Ruff/diff checks passed, no real model
calls were made, and PR/CI publication follows this checkpoint.
