# Submission handoff

Private repository: https://github.com/Mher-1902/questionnaire-evidence-review

Final runtime: Cohere Command A (`command-a-03-2025`). The separate Command A+ pilot is on
`experiment/cohere-command-a-plus` and unmerged draft PR #3. The final main branch contains
the required C workflow, measured lexical RAG, keyless real-response replay, and tested
container/source delivery.

Verification checkpoint:
- 42 tests passed, including UI review/edit/reuse, source races, and credential canaries.
- 18 selected real responses passed independent expectations and coding-assistant source inspection.
- All five required scripted demonstrations passed with zero new model calls.
- Linux container build, keyless replay, health, credential exclusion, and approval persistence
  across recreation passed in CI.
- Main delivery run 37943987430 passed; the downloadable package is available in its artifacts.

The source inspection is AI-assisted. Scripted acknowledgements are simulations; inspect the
answers yourself and approve through the local workspace. These examples do not prove general
accuracy, authenticated production operation, or load capacity.

Before sending the submission, obtain the reviewer's GitHub identity and arrange access to
the private repository. No invitation or recruiter message has been sent automatically.
If access is inconvenient, the sanitized delivery package can be supplied through an agreed
channel. It includes setup instructions and replay, and does not need the candidate's key.

Suggested message for the candidate to send after access is arranged:

> Hello Anastasiia, I've completed Assignment C, the Questionnaire Evidence & Review Workspace.
> The repository includes setup instructions, saved real Cohere responses for keyless replay,
> a written walkthrough, and expected-versus-observed checks. It also includes the AI workflow
> configuration, recorded time, and known limitations. Please let me know which GitHub account
> should receive access to the private repository.

This is a draft only; it has not been sent.
