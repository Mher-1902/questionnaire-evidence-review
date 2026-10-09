"""Explicit live capture. Only successful real HTTP responses become replay files."""

import argparse
import json
import time

from evidence_review.domain import load_dataset
from evidence_review.provider import Provider
from evidence_review.settings import ROOT, Settings
from evidence_review.storage import Store
from evidence_review.workflow import Workflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["retrieval", "full_context"], default="retrieval")
    parser.add_argument("--question", default="all")
    parser.add_argument("--model", default=None, help="Explicit, recorded model-access preflight")
    parser.add_argument("--pace", type=float, default=6.2)
    parser.add_argument("--missing-only", action="store_true")
    args = parser.parse_args()
    settings = Settings.load()
    if args.model:
        settings = settings.model_copy(update={"model_id": args.model})
    store = Store(ROOT / ".runtime/review.sqlite")
    try:
        _, data = store.snapshot()
    except ValueError:
        data = load_dataset((ROOT / "fixtures/questionnaire.json").read_bytes())
        store.import_dataset(data)
    workflow = Workflow(store, Provider(settings, store))
    questions = data.questions if args.question == "all" else [data.question(args.question)]
    failures = 0
    for index, question in enumerate(questions):
        if args.missing_only:
            existing = workflow.ask(question.id, mode="replay", strategy=args.strategy, force=True)
            if existing["status"] != "error":
                print(
                    json.dumps(
                        {
                            "question_id": question.id,
                            "status": existing["status"],
                            "origin": "existing-real-recording",
                            "provider_attempts": 0,
                        }
                    ),
                    flush=True,
                )
                continue
        result = workflow.ask(question.id, mode="live", strategy=args.strategy, force=True)
        metadata = result["metadata"]
        print(
            json.dumps(
                {
                    "question_id": question.id,
                    "status": result["status"],
                    "strategy": args.strategy,
                    "elapsed_ms": metadata.get("elapsed_ms"),
                    "provider_attempts": metadata.get("provider_attempts"),
                    "usage": metadata.get("new_provider_usage"),
                    "error": metadata.get("error"),
                    "structural_errors": metadata.get("structural_errors", []),
                }
            ),
            flush=True,
        )
        failures += result["status"] == "error"
        if result["status"] == "error" and metadata.get("error_code") in {
            "authentication",
            "model_unavailable",
            "request_rejected",
            "local_limit",
        }:
            break
        if index + 1 < len(questions):
            time.sleep(max(0, min(args.pace, 60)))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
