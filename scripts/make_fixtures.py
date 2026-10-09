"""Deterministic, fictional extensions; original starter files are never modified."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    original = json.loads((ROOT / "client-ai-starter-pack/tasks/evidence/seed.json").read_text())
    data = copy.deepcopy(original)
    data["questions"].append(
        {
            "id": "Q9",
            "topic": "billing",
            "text": "How often are paid subscriptions billed, and when is email support available?",
        }
    )
    directory = ROOT / "fixtures"
    directory.mkdir(exist_ok=True)
    (directory / "questionnaire.json").write_text(json.dumps(data, indent=2) + "\n")
    scenarios = directory / "scenarios"
    scenarios.mkdir(exist_ok=True)
    for name in [
        "version-change",
        "date-only",
        "authority-change",
        "text-change",
        "uncited-conflict",
    ]:
        changed = copy.deepcopy(data)
        if name == "version-change":
            changed["documents"][1]["version"] += 1
        elif name == "date-only":
            changed["documents"][1]["date"] = "2025-01-01"
        elif name == "authority-change":
            changed["documents"][1]["supersedes"] = None
        elif name == "text-change":
            changed["documents"][2]["passages"][0]["text"] = (
                "Email support is available Monday to Friday, 10:00 to 17:00 UTC. "
                "Live chat is not offered."
            )
        else:
            changed["documents"].append(
                {
                    "id": "SUPPORT-ALTERNATE",
                    "version": 1,
                    "date": "2026-08-02",
                    "status": "current",
                    "supersedes": None,
                    "passages": [
                        {
                            "id": "SUPPORT-ALTERNATE:p1",
                            "text": "Email support is available on Saturday and Sunday only.",
                        }
                    ],
                }
            )
        (scenarios / f"{name}.json").write_text(json.dumps(changed, indent=2) + "\n")


if __name__ == "__main__":
    main()
