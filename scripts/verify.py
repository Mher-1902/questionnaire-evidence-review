"""Keyless expected-versus-observed checks and a small real-response comparison."""

import json
import statistics
import tempfile
from pathlib import Path

from pydantic import SecretStr

from evidence_review.domain import Answer, Authority, load_dataset, validate_evidence
from evidence_review.provider import Provider, ProviderError
from evidence_review.settings import ROOT, Settings
from evidence_review.storage import Store, now
from evidence_review.workflow import Workflow


def summarize(rows):
    times = [r["recorded_live_elapsed_ms"] for r in rows if r.get("recorded_live_elapsed_ms")]
    tokens = [r["input_tokens"] for r in rows if r.get("input_tokens") is not None]
    return {
        "n": len(rows),
        "successful_cases": sum(r["passed"] for r in rows),
        "mean_input_tokens": statistics.mean(tokens) if tokens else None,
        "live_latency_median_ms": statistics.median(times) if times else None,
        "live_latency_range_ms": [min(times), max(times)] if times else None,
    }


def main():
    data = load_dataset((ROOT / "fixtures/questionnaire.json").read_bytes())
    expectations = json.loads((ROOT / "fixtures/expected.json").read_text())["cases"]
    reviews = json.loads((ROOT / "docs/source-review.json").read_text())
    settings = Settings.load().model_copy(update={"api_key": SecretStr("")})
    report = {
        "generated_at": now(),
        "model": settings.model_id,
        "new_provider_calls": 0,
        "semantic_review_method": reviews["method"],
        "cases": [],
        "demonstrations": [],
        "limitations": [
            "Nine examples do not prove general accuracy or latency.",
            "Source inspection is AI-assisted; actual approval requires human review.",
            "Provider caching and request timing confound latency comparisons.",
            "Workflow approval acknowledgements below are scripted simulations.",
        ],
    }
    with tempfile.TemporaryDirectory() as temporary:
        store = Store(Path(temporary) / "verify.sqlite")
        store.import_dataset(data)
        provider = Provider(settings, store)
        flow = Workflow(store, provider)
        for strategy in ["retrieval", "full_context"]:
            for expected in expectations:
                question = data.question(expected["id"])
                row = {
                    "question_id": question.id,
                    "strategy": strategy,
                    "expected": expected,
                    "passed": False,
                }
                try:
                    text, trace = provider.generate(
                        data, question, mode="replay", strategy=strategy
                    )
                    answer = Answer.model_validate_json(text)
                    errors = validate_evidence(answer, data)
                    citations = {c.passage_id for c in answer.citations}
                    source_check = reviews["reviews"].get(trace["recording"])
                    required = set(expected["required_passages"])
                    state_ok = answer.answerability == expected["answerability"]
                    references_ok = required <= citations
                    if expected.get("historical_passages"):
                        historical = {p for c in answer.conflicts for p in c.passage_ids}
                        references_ok &= set(expected["historical_passages"]) <= historical
                    row |= {
                        "observed": answer.model_dump(),
                        "recording": trace["recording"],
                        "structural_errors": errors,
                        "state_match": state_ok,
                        "required_citations_present": references_ok,
                        "retrieval_required_passage_coverage": len(
                            required & set(trace["included_passages"])
                        )
                        / len(required)
                        if required
                        else None,
                        "source_inspection": source_check,
                        "owner": data.owners[question.topic],
                        "recorded_live_elapsed_ms": trace["recorded_elapsed_ms"],
                        "replay_elapsed_ms": trace["elapsed_ms"],
                        "input_tokens": (trace.get("recorded_usage") or {})
                        .get("tokens", {})
                        .get("input_tokens"),
                        "output_tokens": (trace.get("recorded_usage") or {})
                        .get("tokens", {})
                        .get("output_tokens"),
                        "recorded_usage": trace.get("recorded_usage"),
                        "passed": not errors
                        and state_ok
                        and references_ok
                        and bool(source_check and source_check["passed"]),
                    }
                except (ProviderError, ValueError) as error:
                    row["error"] = str(error)
                report["cases"].append(row)

        report["demonstrations"].append(
            {
                "check": "supported-citations",
                "expected": "Q3 is supported with its existing support passage",
                "passed": any(
                    r["question_id"] == "Q3" and r["strategy"] == "retrieval" and r["passed"]
                    for r in report["cases"]
                ),
            }
        )
        report["demonstrations"].append(
            {
                "check": "unknown-route",
                "expected": "Q2 remains unknown and routes to Product reviewer",
                "passed": any(
                    r["question_id"] == "Q2"
                    and r["strategy"] == "retrieval"
                    and r["passed"]
                    and r["owner"] == "Product reviewer"
                    for r in report["cases"]
                ),
            }
        )
        report["demonstrations"].append(
            {
                "check": "explicit-replacement",
                "expected": "Q1 cites the explicit replacement "
                "and preserves historical disagreement",
                "passed": Authority(data).current("EXPORT-v1") == "EXPORT-v2"
                and any(
                    r["question_id"] == "Q1" and r["strategy"] == "retrieval" and r["passed"]
                    for r in report["cases"]
                ),
            }
        )
        result = flow.ask("Q1", mode="replay")
        if result.get("answer"):
            corrected = result["answer"].model_copy(
                update={
                    "answer": "No. Only paid-plan users can export CSV; free-plan users cannot."
                }
            )
            draft = store.save_draft(
                data.question("Q1"), corrected, store.snapshot()[0], "scripted-review-simulation"
            )
            store.approve(draft, "Scripted demo reviewer", semantic_confirmed=True)
            unapproved = corrected.model_copy(update={"answer": "Unapproved working edit"})
            store.save_draft(
                data.question("Q1"), unapproved, store.snapshot()[0], "unapproved-simulation"
            )
            reused = flow.ask("Q1", mode="replay")
            report["demonstrations"].append(
                {
                    "check": "approved-correction-reuse",
                    "expected": corrected.answer,
                    "observed": reused["answer"].answer,
                    "new_provider_calls": reused["metadata"]["provider_attempts"],
                    "elapsed_ms": reused["metadata"]["elapsed_ms"],
                    "passed": reused["answer"].answer == corrected.answer
                    and reused["metadata"]["provider_attempts"] == 0,
                }
            )
            restarted = Store(store.path)
            preserved = restarted.reusable(data.question("Q1"))
            restarted.import_dataset(
                load_dataset((ROOT / "fixtures/scenarios/version-change.json").read_bytes())
            )
            stale = restarted.latest_approval(data.question("Q1"))
            report["demonstrations"].append(
                {
                    "check": "restart-and-version-invalidation",
                    "expected": "Approval survives restart; referenced version change blocks reuse",
                    "observed": {
                        "persisted": bool(preserved),
                        "stale": bool(stale["stale"]),
                        "changes": restarted.review_changes(stale["id"]),
                    },
                    "passed": bool(preserved) and not restarted.reusable(data.question("Q1")),
                }
            )
        report["new_provider_calls"] = store.attempt_count()
    report["comparison"] = {
        strategy: summarize([r for r in report["cases"] if r["strategy"] == strategy])
        for strategy in ["retrieval", "full_context"]
    }
    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    (output / "verification.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    lines = [
        "# Expected versus observed",
        "",
        "Generated without provider calls.",
        "",
        "Semantic checks are coding-assistant source inspection, "
        "not automatic entailment or human approval.",
        "",
        "| Question | Strategy | State | Required citations | Source inspection | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["cases"]:
        state = row.get("observed", {}).get("answerability", "error")
        references = row.get("required_citations_present", False)
        inspected = bool(row.get("source_inspection"))
        lines.append(
            f"| {row['question_id']} | {row['strategy']} | {state} | "
            f"{references} | {inspected} | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines += ["", "## Required demonstrations", ""]
    lines += [
        f"- {r['check']}: {'PASS' if r['passed'] else 'FAIL'} — {r['expected']}"
        for r in report["demonstrations"]
    ]
    lines += ["", "## Limits", ""] + ["- " + limit for limit in report["limitations"]]
    (output / "verification.md").write_text("\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "cases_passed": sum(r["passed"] for r in report["cases"]),
                "cases_total": len(report["cases"]),
                "demonstrations": report["demonstrations"],
                "comparison": report["comparison"],
                "new_provider_calls": report["new_provider_calls"],
            }
        )
    )
    raise SystemExit(
        0
        if all(r["passed"] for r in report["cases"])
        and len(report["demonstrations"]) == 5
        and all(r["passed"] for r in report["demonstrations"])
        else 1
    )


if __name__ == "__main__":
    main()
