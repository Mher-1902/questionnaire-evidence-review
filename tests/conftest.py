import json
from pathlib import Path

import pytest

from evidence_review.domain import Answer, Dataset
from evidence_review.storage import Store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw():
    return json.loads((ROOT / "fixtures/questionnaire.json").read_text())


@pytest.fixture
def data(raw):
    return Dataset.model_validate(raw)


@pytest.fixture
def store(tmp_path, data):
    store = Store(tmp_path / "state.sqlite")
    store.import_dataset(data)
    return store


@pytest.fixture
def supported():
    return Answer(
        answer="No. CSV export is available on paid plans only.",
        answerability="supported",
        conflict_resolution="resolved_by_supersession",
        citations=[{"passage_id": "EXPORT-v2:p1", "quote": "Free-plan users cannot export CSV."}],
        conflicts=[
            {
                "passage_ids": ["EXPORT-v1:p1", "EXPORT-v2:p1"],
                "reason": "The explicit replacement restricts the older all-plan policy.",
            }
        ],
        note="",
    )
