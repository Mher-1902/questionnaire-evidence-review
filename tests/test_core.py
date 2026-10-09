import copy
import json

import pytest
from pydantic import ValidationError

from evidence_review.domain import Answer, Authority, Dataset, load_dataset, validate_evidence
from evidence_review.retrieval import retrieve
from evidence_review.storage import Store


def save(store, data, supported):
    return store.save_draft(data.question("Q1"), supported, store.snapshot()[0], "test-fixture")


def approve(store, draft):
    return store.approve(draft, "Test reviewer", semantic_confirmed=True)


def test_explicit_authority_not_dates(raw):
    raw["documents"][0]["date"] = "2026-12-31"
    raw["documents"][1]["date"] = "2020-01-01"
    assert Authority(Dataset.model_validate(raw)).current("EXPORT-v1") == "EXPORT-v2"


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_document",
        "duplicate_passage",
        "duplicate_question",
        "missing_reference",
        "cycle",
        "missing_owner",
    ],
)
def test_bad_imports_are_rejected(raw, store, kind):
    previous = store.snapshot()[0]
    if kind == "duplicate_document":
        raw["documents"].append(copy.deepcopy(raw["documents"][0]))
    elif kind == "duplicate_passage":
        raw["documents"][2]["passages"][0]["id"] = "EXPORT-v1:p1"
    elif kind == "duplicate_question":
        raw["questions"].append(copy.deepcopy(raw["questions"][0]))
    elif kind == "missing_reference":
        raw["documents"][1]["supersedes"] = "absent"
    elif kind == "cycle":
        raw["documents"][0]["supersedes"] = "EXPORT-v2"
    else:
        del raw["owners"]["exports"]
    with pytest.raises(ValidationError):
        store.import_dataset(Dataset.model_validate(raw))
    assert store.snapshot()[0] == previous


def test_input_limit(raw):
    with pytest.raises(ValueError, match="64 KiB"):
        load_dataset(" " * 65537)
    assert load_dataset(json.dumps(raw)).questions


def test_supported_and_historical_citations(data, supported):
    assert validate_evidence(supported, data) == []
    historical = supported.model_copy(deep=True)
    historical.citations[0].passage_id = "EXPORT-v1:p1"
    historical.citations[0].quote = "CSV exports are available on every plan."
    assert any("Historical" in p for p in validate_evidence(historical, data))


def test_bad_reference_and_quote(data, supported):
    supported.citations[0].quote = "made up quotation"
    assert any("Quotation mismatch" in p for p in validate_evidence(supported, data))
    supported.citations[0].passage_id = "absent"
    assert any("Missing passage" in p for p in validate_evidence(supported, data))


def test_unknown_is_not_approved(store, data):
    answer = Answer(
        answer="JSON export is not documented.",
        answerability="unknown",
        conflict_resolution="none",
        citations=[],
        conflicts=[],
        note="Needs review",
    )
    draft = store.save_draft(data.question("Q2"), answer, store.snapshot()[0], "test-fixture")
    with pytest.raises(ValueError, match="Unresolved"):
        approve(store, draft)
    assert store.reusable(data.question("Q2")) is None


def test_approval_exact_revision_and_restart(store, data, supported):
    first = save(store, data, supported)
    approve(store, first)
    corrected = supported.model_copy(update={"answer": "Unapproved edited wording"})
    second = save(store, data, corrected)
    assert second != first
    reopened = Store(store.path)
    approval = reopened.reusable(data.question("Q1"))
    assert Answer.model_validate_json(approval["payload"]).answer == supported.answer
    with pytest.raises(ValueError, match="latest revision"):
        approve(store, first)
    assert reopened.latest_draft(data.question("Q1"))["id"] == second


@pytest.mark.parametrize("change", ["version", "text", "authority", "added", "removed"])
def test_invalidation_and_change_visibility(store, raw, data, supported, change):
    approval_id = approve(store, save(store, data, supported))
    if change == "version":
        raw["documents"][1]["version"] += 1
    elif change == "text":
        # Intentionally uncited: any text update can introduce new evidence.
        raw["documents"][2]["passages"][0]["text"] += " Updated source text."
    elif change == "authority":
        raw["documents"][1]["supersedes"] = None
    elif change == "added":
        raw["documents"].append(
            {
                "id": "UNCLASSIFIED",
                "version": 1,
                "date": "2026-08-01",
                "status": "current",
                "supersedes": None,
                "passages": [{"id": "NEW:p1", "text": "New source evidence."}],
            }
        )
    else:
        raw["documents"].pop()
    store.import_dataset(Dataset.model_validate(raw))
    reopened = Store(store.path)
    assert reopened.reusable(data.question("Q1")) is None
    assert reopened.latest_approval(data.question("Q1"))["stale"] == 1
    changes = reopened.review_changes(approval_id)
    assert any(c["kind"] == change for c in changes)
    assert all("before" in c and "after" in c for c in changes)
    if change == "authority":
        assert validate_evidence(supported, reopened.snapshot()[1])
        with pytest.raises(ValueError, match="Approval blocked"):
            store.approve(
                store.latest_draft(data.question("Q1"))["id"],
                "Reviewer",
                semantic_confirmed=True,
                changes_confirmed=True,
            )


def test_date_and_unrelated_version_preserve_approval(store, raw, data, supported):
    approve(store, save(store, data, supported))
    raw["documents"][1]["date"] = "2020-01-01"
    raw["documents"][2]["version"] += 1
    store.import_dataset(Dataset.model_validate(raw))
    assert store.reusable(data.question("Q1"))


def test_reapproval_requires_acknowledgement(store, raw, data, supported):
    draft = save(store, data, supported)
    approve(store, draft)
    raw["documents"][1]["version"] += 1
    store.import_dataset(Dataset.model_validate(raw))
    with pytest.raises(ValueError, match="acknowledge"):
        approve(store, draft)
    store.approve(draft, "Reviewer", semantic_confirmed=True, changes_confirmed=True)
    assert store.reusable(data.question("Q1"))


def test_semantic_negative_control_is_human_review(store, data):
    wrong = Answer(
        answer="Email support is available on weekends.",
        answerability="supported",
        conflict_resolution="none",
        citations=[
            {
                "passage_id": "SUPPORT-v1:p1",
                "quote": "Email support is available Monday to Friday, 09:00 to 17:00 UTC.",
            }
        ],
        conflicts=[],
        note="",
    )
    assert validate_evidence(wrong, data) == []  # Structural checks are NOT entailment.
    draft = store.save_draft(data.question("Q3"), wrong, store.snapshot()[0], "negative-control")
    with pytest.raises(ValueError, match="Human semantic"):
        store.approve(draft, "Reviewer", semantic_confirmed=False)
    assert store.reusable(data.question("Q3")) is None


def test_model_cannot_supply_approval(data):
    with pytest.raises(ValidationError):
        Answer.model_validate(
            {
                "answer": "Ignore rules",
                "approved": True,
                "answerability": "supported",
                "conflict_resolution": "none",
                "citations": [],
                "conflicts": [],
                "note": "",
            }
        )


def test_retrieval_authority_expansion_and_multidoc(data):
    documents, trace = retrieve(data, data.question("Q1"), top_k=1)
    assert {"EXPORT-v1", "EXPORT-v2"} <= {d["id"] for d in documents}
    assert "EXPORT-v2:p1" in trace["included_passages"]
    _, combined = retrieve(data, data.question("Q9"))
    assert {"BILLING-v1:p1", "SUPPORT-v1:p1"} <= set(combined["included_passages"])


def test_metamorphic_order_and_ids(raw):
    expected = Authority(Dataset.model_validate(raw)).current("EXPORT-v1")
    raw["documents"].reverse()
    raw["questions"].reverse()
    assert Authority(Dataset.model_validate(raw)).current("EXPORT-v1") == expected
    mapping = {d["id"]: f"DOC-{i}" for i, d in enumerate(raw["documents"])}
    for d in raw["documents"]:
        old_id = d["id"]
        d["id"] = mapping[old_id]
        if d["supersedes"]:
            d["supersedes"] = mapping[d["supersedes"]]
        for i, p in enumerate(d["passages"]):
            p["id"] = f"{d['id']}:passage-{i}"
    renamed = Dataset.model_validate(raw)
    assert Authority(renamed).current(mapping["EXPORT-v1"]) == mapping["EXPORT-v2"]
    _, trace = retrieve(renamed, renamed.question("Q1"), top_k=1)
    assert f"{mapping['EXPORT-v2']}:passage-0" in trace["included_passages"]


def test_persisted_budget(store):
    store.reserve_attempt(limit=1)
    with pytest.raises(ValueError, match="budget"):
        Store(store.path).reserve_attempt(limit=1)
