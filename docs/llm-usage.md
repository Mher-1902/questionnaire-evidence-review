# LLM usage note

AI tools assisted with research, planning, implementation, and verification. The supplied
fictional seeds and domain rules remain authoritative and unchanged. Complete chat logs,
personal account settings, and credentials are not submitted.

## Tools, models, and roles

| Tool or model | Use in this exercise | Version/configuration record |
| --- | --- | --- |
| Codex | Coding, implementation, debugging, regression tests, Git/CI delivery, and verification. Shell/file tools, documentation browsing, and computer use supported this work. | Exercise instructions are in `AGENTS.md`; relevant environment details are in `ai-workflow/snapshots/environment.md`. Exact active coding-model and desktop-build identifiers were not exposed by the task tools. |
| Claude Code | Architecture, overall project structure, and build planning. | Candidate-reported planning use; exact underlying Claude model, tool version, and session settings were not recorded. |
| Perplexity | Company and technical research supporting planning and assignment selection. | Candidate-reported research use; exact selected model and product version were not recorded. |
| Gemini | Brainstorming and working through lengthy planning/context material. | Candidate-reported planning use; exact model and product version were not recorded. |
| Cohere Command A | The application's actual LLM: proposes evidence-grounded questionnaire drafts and supplies saved real responses for keyless replay. | Final model: `command-a-03-2025`, temperature 0, maximum 1,000 output tokens, JSON-object output, no streaming; see `app-config.toml` and `prompts/`. |
| Cohere Command A+ | An alternate-model pilot retained for comparison. | `command-a-plus-05-2026`, thinking disabled, on `experiment/cohere-command-a-plus` and unmerged draft PR #3. |

The candidate supplied the Claude Code, Perplexity, and Gemini usage details. Those external
sessions and their configuration exports are not included in the repository. They informed
planning/research; implementation and fixes made in the recorded Codex workflow are attributed
to Codex. Gemini was used for brainstorming with long context.

## AI-assisted components

Codex generated and revised application code (`app.py` and `evidence_review/`), the runtime
prompt and output contract, deterministic fixture-generation code and additional test scenarios,
tests, verification scripts, CI/container/launcher/package configuration, and documentation.
Claude Code assisted with the architectural structure and build plan, while Perplexity and
Gemini supported research and brainstorming as described above. Original starter seeds and
rules were preserved; application answers are not hardcoded from the reference cases.

## Representative instruction and workflow

The committed development instruction was:

> Models propose drafts. Application code controls approval, freshness, and reuse.

Development followed the accepted Assignment C plan: preserve supplied source IDs and rules,
implement retrieval and a separately versioned system prompt, validate model output locally,
persist review revisions, and reuse only exact approved wording with current evidence. Changes
were checked, committed on branches, pushed, and merged through passing PR checks. The final
runtime remains Cohere; the development assistants are not dependencies of the application.

## One correction and verification step

An independent inspection found that the draft editor allowed answerability changes but
kept the model's conflict decision unchanged. Codex reproduced that failure and added editable
conflict decisions, passages, and explanations. The regression test first confirms that unresolved
or unrelated-source conflicts cannot be approved, then corrects the replacement evidence,
approves a new revision, and verifies exact zero-call reuse while preserving the original history.

The corrected application passed 63 tests, all 18 selected real-response replay cases, and the
five required demonstrations. Provider failure tests use simulated transport; scripted approval
acknowledgements are simulations. Citation checks and AI-assisted source inspections do not
replace human semantic review. See `docs/inspection-follow-up.md` and `reports/verification.md`.

The completed configuration inventory, relevant versions, unused components, and sanitized
environment examples are indexed by `ai-workflow/manifest.json` and `ai-workflow/README.md`.
