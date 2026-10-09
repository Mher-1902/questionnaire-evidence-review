"""Scripted keyless approval/persistence check; never claims human approval."""

import argparse
import json
import os
from pathlib import Path

from pydantic import SecretStr

from evidence_review.domain import load_dataset
from evidence_review.provider import Provider
from evidence_review.settings import ROOT, Settings
from evidence_review.storage import Store
from evidence_review.workflow import Workflow

CORRECTION = "No. CSV exports require a paid plan; free-plan users cannot export CSV."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["approve", "reuse"])
    args = parser.parse_args()
    store = Store(Path(os.environ.get("APP_STATE_DIR", ROOT / ".runtime")) / "review.sqlite")
    try:
        _, data = store.snapshot()
    except ValueError:
        data = load_dataset((ROOT / "fixtures/questionnaire.json").read_bytes())
        store.import_dataset(data)
    settings = Settings.load().model_copy(update={"api_key": SecretStr("")})
    flow = Workflow(store, Provider(settings, store))
    if args.phase == "approve":
        result = flow.ask("Q1", mode="replay")
        assert result["status"] == "draft"
        corrected = result["answer"].model_copy(update={"answer": CORRECTION})
        draft = store.save_draft(
            data.question("Q1"), corrected, store.snapshot()[0], "scripted-container-simulation"
        )
        store.approve(draft, "Scripted container check", semantic_confirmed=True)
    else:
        result = flow.ask("Q1", mode="replay")
        assert result["metadata"]["origin"] == "approved_reuse"
        assert result["answer"].answer == CORRECTION
    assert store.attempt_count() == 0
    print(
        json.dumps(
            {
                "phase": args.phase,
                "passed": True,
                "provider_calls": 0,
                "scope": "Scripted workflow acknowledgement, not human approval",
            }
        )
    )


if __name__ == "__main__":
    main()
