# Written walkthrough

Run `uv sync --locked` and `uv run streamlit run app.py`, or `docker compose up --build`.
Start in Saved real responses mode. No API key is needed.

1. Click **Draft pending questions**. Q3 gives weekday support hours, with the existing
   support passage and exact quotation beside it. The draft remains unapproved.
2. Select Q2. JSON export remains unknown and routes to Product reviewer. An empty answer
   with an explanatory note is a legitimate unresolved result, not an invented No.
3. Select Q1. Inspect EXPORT-v2, its explicit replacement of EXPORT-v1, and the old
   all-plan policy. Dates do not decide which source wins.
4. Edit Q1 to “No. CSV exports require a paid plan; free-plan users cannot export CSV.”
   Save the draft, inspect its quotation, check semantic confirmation, and approve.
   Click **Answer / reuse**. The exact approved wording returns with zero provider attempts.
5. Save another edit without approval. Asking again still returns the previously approved
   wording. The unapproved revision stays visible in history.
6. Restart the application. Approval and its source snapshot remain. Import
   `fixtures/scenarios/version-change.json`. The approval now needs review, reuse is blocked,
   and the evidence card shows the changed version. Reapproval requires inspecting changes.
7. Import the authority-change scenario. Removing `supersedes` leaves a source-authority
   problem even though text is unchanged; clearing model conflict fields cannot bypass it.
8. Inspect the uncited-conflict scenario. Newly added evidence invalidates approvals and
   appears in the change view, including evidence not originally cited.

`uv run python scripts/verify.py` reproduces the five required checks in an isolated database.
Its scripted approval acknowledgement is a simulation. Source inspection is AI-assisted;
real human approval occurs only through explicit review in the app.

The comparison uses nine questions per strategy, including Q9's two-document synthesis.
Retrieval reduced input tokens by about 12.2% in these recordings, but its median successful
call was slower. Do not turn that small sample into a throughput or accuracy claim.

One important negative control claims weekend support while quoting the genuine weekday
passage. Structural checks pass. Semantic confirmation is deliberately withheld in the
scripted test, preventing approval. The validator does not automatically establish meaning.

The separate Command A+ experiment is preserved in draft PR #3. It correctly answered the
pilot question but omitted historical disagreement in its fields; main uses Cohere Command A.
