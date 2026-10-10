# Submission handoff

Public repository: https://github.com/Mher-1902/questionnaire-evidence-review

AI usage note: https://github.com/Mher-1902/questionnaire-evidence-review/blob/main/docs/llm-usage.md

Final runtime: Cohere Command A (`command-a-03-2025`). The separate Command A+ pilot is on
`experiment/cohere-command-a-plus` and unmerged draft PR #3. The final main branch contains
the required C workflow, measured lexical RAG, keyless real-response replay, and tested
container/source delivery.

Verification checkpoint:
- 63 tests passed, including the four inspection fixes, UI review/edit/reuse, source races,
  and credential canaries.
- 18 selected real responses passed independent expectations and coding-assistant source inspection.
- All five required scripted demonstrations passed with zero new model calls.
- Linux container build, keyless replay, health, credential exclusion, and approval persistence
  across recreation passed in CI.
- The inspection follow-up and reproductions are documented in
  [inspection-follow-up.md](inspection-follow-up.md).

The corrected application on main commit `b0ddccfd63dddf78b4020391146b9e571f1b8e3e`
passed all four jobs in [run 38029175559](https://github.com/Mher-1902/questionnaire-evidence-review/actions/runs/38029175559),
completed 10 October 2026 at 05:57:33 UTC. The documentation and manifest update follows
that verified code checkpoint.

The final CI-produced archive's `delivery-manifest.json` records its exact source commit,
archive filename, and producing verification-run URL. Check that run's successful conclusion
and all four jobs before using its artifact. This remains accurate after documentation-only
commits; a prior checkpoint is not presented as the final archive's verification.

Start with `./full_run.sh`: it sets up a project-local Python environment, installs locked
dependencies, runs the checks, and starts the app. Saved real responses need no API key.
The localhost address is accessible only on the machine running the application; there is
no hosted deployment. The public repository is durable; CI artifacts expire after seven days.

The work log records measured build intervals and untimed preparation. Follow-up fixes on
10 October are additional work after inspection; do not describe the full exercise as
proven to fit eight hours.

The source inspection is AI-assisted. Scripted acknowledgements are simulations; inspect the
answers yourself and approve through the local workspace. These examples do not prove general
accuracy, authenticated production operation, or load capacity.

The repository was made public on 10 October 2026 at the candidate's explicit request.
Reviewers can read the source and submission documents directly. The sanitized delivery
package can also be supplied through an agreed channel; it includes setup instructions and
replay and does not need the candidate's key. No recruiter message has been sent automatically.

Suggested message for the candidate to send:

> Hello Anastasiia, I've completed Assignment C, the Questionnaire Evidence & Review Workspace.
> The repository includes setup instructions, saved real Cohere responses for keyless replay,
> a written walkthrough, and expected-versus-observed checks. It also includes the AI workflow
> configuration, recorded time, and known limitations. Repository:
> https://github.com/Mher-1902/questionnaire-evidence-review

This is a draft only; it has not been sent.
