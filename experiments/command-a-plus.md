# Command A+ pilot — separate experimental branch

Run one real question through the existing Cohere adapter:

```bash
uv run python scripts/capture_live.py --question Q1 --model command-a-plus-05-2026
```

The active application configuration remains `command-a-03-2025`. The explicit CLI
override changes the pilot model only. The saved request records the exact prompt,
JSON-object configuration, disabled thinking, evidence, and model ID.

Observed pilot: the answer correctly says free-plan users cannot export CSV and cites
the replacement passage. It passed structural/reference checks, but returned no
historical disagreement in its conflict fields. The application independently preserves
replacement-family passages; the primary Command A recording explicitly reported the
historical disagreement as required by the reference case.

This is one pilot, not a model-quality or latency benchmark. Different tokenizers and
provider caching make cross-model token/latency comparisons especially limited.
See `command-a-plus-result.json` and its real response file. Earlier rejected preflights
are retained in the parent implementation's records. Keep this experiment unmerged;
the final application uses Cohere Command A and its complete nine-question verification.
