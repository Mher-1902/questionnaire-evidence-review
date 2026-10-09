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
