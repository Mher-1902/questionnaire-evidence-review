# Questionnaire Evidence & Review

Assignment C: a local workspace for grounded questionnaire drafts, human review,
approved-answer reuse, and visible source-change invalidation.

Implementation is in progress. The supplied fictional rules and original seeds are retained
under `client-ai-starter-pack/tasks/evidence/`. Only Assignment C is included.

## Development

Python 3.12 and uv are required. Dependencies will be committed in `uv.lock`.
The default demonstration will use saved real responses without an API key.
Live generation uses `MODEL_API_KEY` from the ignored `.env` file.

The project uses focused feature branches and PRs, with verification recorded throughout.
See `AGENTS.md` for the exercise-specific development constraints.
