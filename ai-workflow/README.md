# AI workflow used for Assignment C

## Tools and models

Development used the Codex coding assistant with shell/file tools, official-documentation
browsing, and Codex app PR attachment. Earlier planning used a read-only research council;
implementation was performed by the primary assistant. Exact coding-model/desktop build
identifiers are not exposed by these task tools and are marked not-exportable.

Application runtime uses Cohere `command-a-03-2025` through HTTPX 0.28.1. The application
uses JSON-object output, temperature 0, maximum 1,000 tokens, no streaming, and strict local
validation. Command A omits thinking parameters. The separate Command A+ pilot uses
`command-a-plus-05-2026` with thinking disabled and is preserved on its experimental branch.
It is not the final application configuration.

Pinned environment: Python 3.12.15, Streamlit 1.65.0, Pydantic 2.14.0, python-dotenv 1.2.4,
pytest 9.1.1, Ruff 0.16.10, pip-audit 2.10.1, uv 0.12.24, GitHub CLI 2.102.0,
and Gitleaks 8.30.1. `uv.lock` records the complete dependency versions and hashes.
Docker bases and GitHub Actions are pinned to immutable digests/commit SHAs.

## Configuration and versions

`AGENTS.md` contains the project-specific development instructions. The starter's
`generate-assignment-data/SKILL.md` was used as a fixture-preparation reference, without
installation or global AI-setting changes. Original inputs remain unchanged; the deterministic
fixture script and independent expectations are committed.

Application instructions are in `prompts/system.md`; the output contract is in
`prompts/answer-schema.json`. The provider appends the contract to the system instruction
and supplies question/documents separately as JSON user data. Prompt/contract hashes and
exact requests are preserved with real responses. Earlier settings and prompt wording are
also saved under `snapshots/` and through Git history.

No AI hooks or custom runtime agents were created. No MCP server is part of the application.
The coding environment's provider-managed tool configurations and permission rules are
not exportable; the relevant behavior is summarized in `snapshots/environment.md`.
Only relevant project configuration is submitted, not a personal configuration directory.
API keys, GitHub credentials, private user settings, and unrelated research attachments
are excluded. Environment examples list variable names with blank/dummy values.

## One actual verification-and-correction example

The development instruction was to implement the accepted data-driven review workflow:
“Models propose drafts. Application code controls approval, freshness, and reuse.”
`AGENTS.md` and the system prompt reinforced that instruction.

The first real Command A+ response included reasoning outside JSON. The application rejected
it rather than extracting a convenient trailing object. A Command A preflight omitted
historical conflict references; explicit field-consistency instructions were added and checked
against a new real response. An unknown JSON-export response contained no answer but a useful
explanation; the local contract was corrected to permit that unresolved representation while
continuing to reject empty supported answers. Intermittent provider generation failures remained
visible and were not recast as product uncertainty.

After selecting JSON-object output with local validation, nine questions were captured under
retrieval and full-context strategies. All 18 selected responses were checked against independent
expectations and source passages. Source inspection was coding-assistant work, not a claim of
human approval. The interface still requires the person reviewing an answer to confirm meaning.

## Reproduce and replay

```bash
uv sync --locked
uv run pytest
uv run python scripts/verify.py
uv run streamlit run app.py
```

No key is needed for replay or checks. `MODEL_API_KEY` is needed only for explicitly selected
live generation. `APP_STATE_DIR` optionally chooses local storage. Request changes require
matching real recordings; missing replay never triggers a live call. Restore earlier experiments
from named snapshots or Git history, and use their matching recordings rather than claiming
they reproduce the current configuration.

## Decisions and limitations

The small local collection supports measurable lexical retrieval without embeddings. Explicit
replacement metadata, durable review, and zero-call approved reuse are the important workflow
controls. CI and container checks exercise reproducibility; AWS operation, verified identities,
distributed quotas, and production workload tests are not demonstrated. Original preparatory
research duration was not instrumented; see the honest time record.
