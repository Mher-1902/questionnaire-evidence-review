from streamlit.testing.v1 import AppTest

from evidence_review.domain import Answer
from evidence_review.settings import ROOT
from evidence_review.storage import Store


def button(app, label):
    return next(item for item in app.button if item.label == label)


def start(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("MODEL_API_KEY", "")
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def test_keyless_ui_start_and_reruns_do_not_call_provider(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    assert not app.exception
    assert app.metric[0].value == "9"
    app.run()
    assert not app.exception
    assert Store(tmp_path / "review.sqlite").attempt_count() == 0


def test_review_edit_approve_reuse_through_ui(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    button(app, "Answer / reuse").click().run()
    assert not app.exception
    assert button(app, "Approve exact saved revision").disabled
    wording = "No. CSV export is available only on paid plans."
    next(item for item in app.text_area if item.label == "Answer wording").set_value(wording)
    button(app, "Save edited draft").click().run()
    assert not app.exception
    app.checkbox[0].check().run()
    button(app, "Approve exact saved revision").click().run()
    assert not app.exception
    store = Store(tmp_path / "review.sqlite")
    assert wording in store.reusable(store.snapshot()[1].question("Q1"))["payload"]
    button(app, "Answer / reuse").click().run()
    assert not app.exception
    assert store.attempt_count() == 0
    assert store.runs()[0]["metadata"]["origin"] == "approved_reuse"


def test_new_revision_resets_semantic_confirmation(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    button(app, "Answer / reuse").click().run()
    app.checkbox[0].check().run()
    assert not button(app, "Approve exact saved revision").disabled
    next(item for item in app.text_area if item.label == "Answer wording").set_value(
        "Free-plan users cannot export CSV."
    )
    button(app, "Save edited draft").click().run()
    assert not app.exception
    assert not app.checkbox[0].value
    assert button(app, "Approve exact saved revision").disabled


def test_fake_credential_not_rendered(monkeypatch, tmp_path):
    canary = "FAKE-CREDENTIAL-CANARY-not-a-real-key"
    monkeypatch.setenv("APP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("MODEL_API_KEY", canary)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    button(app, "Answer / reuse").click().run()
    assert not app.exception
    rendered = "".join(
        str(item.value)
        for collection in [app.text, app.caption, app.error, app.json, app.code]
        for item in collection
    )
    assert canary not in rendered
    assert Store(tmp_path / "review.sqlite").attempt_count() == 0


def test_mistaken_conflict_can_be_corrected_approved_and_reused(monkeypatch, tmp_path, supported):
    app = start(monkeypatch, tmp_path)
    store = Store(tmp_path / "review.sqlite")
    dataset_id, data = store.snapshot()
    question = data.question("Q1")
    mistaken = supported.model_copy(
        deep=True,
        update={"answerability": "conflicted", "conflict_resolution": "unresolved"}
    )
    mistaken.conflicts[0].passage_ids = ["EXPORT-v1:p1", "SUPPORT-v1:p1"]
    first = store.save_draft(question, mistaken, dataset_id, "test-fixture")
    app.run()
    next(item for item in app.selectbox if item.label == "Evidence decision").select("supported")
    button(app, "Save edited draft").click().run()
    next(item for item in app.checkbox if item.label.startswith("I checked")).check().run()
    button(app, "Approve exact saved revision").click().run()
    assert any("unresolved conflict" in item.value for item in app.error)
    assert store.reusable(question) is None
    next(item for item in app.selectbox if item.label == "Conflict decision").select(
        "resolved_by_supersession"
    )
    button(app, "Save edited draft").click().run()
    next(item for item in app.checkbox if item.label.startswith("I checked")).check().run()
    button(app, "Approve exact saved revision").click().run()
    assert any("not resolved by explicit replacement" in item.value for item in app.error)
    assert store.reusable(question) is None
    next(item for item in app.multiselect if item.label == "Conflict passages 1").set_value(
        ["EXPORT-v1:p1", "EXPORT-v2:p1"]
    )
    next(item for item in app.text_area if item.label == "Conflict explanation 1").set_value(
        "EXPORT-v2 explicitly replaces EXPORT-v1; retain both passages for review."
    )
    button(app, "Save edited draft").click().run()
    next(item for item in app.checkbox if item.label.startswith("I checked")).check().run()
    button(app, "Approve exact saved revision").click().run()
    assert not app.exception
    approved = Answer.model_validate_json(store.reusable(question)["payload"])
    assert approved.answer == supported.answer
    assert approved.conflict_resolution == "resolved_by_supersession"
    assert approved.conflicts[0].passage_ids == ["EXPORT-v1:p1", "EXPORT-v2:p1"]
    assert Answer.model_validate_json(store.revisions(question)[-1]["payload"]) == mistaken
    assert store.revisions(question)[-1]["id"] == first
    button(app, "Answer / reuse").click().run()
    assert not app.exception
    assert store.runs()[0]["metadata"]["origin"] == "approved_reuse"
    assert store.attempt_count() == 0


def test_unresolved_note_before_generation_updates_queue(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    next(item for item in app.text_area if item.label == "Review note").set_value(
        "Ask the product reviewer to confirm the evidence."
    )
    button(app, "Leave unresolved with note").click().run()
    assert not app.exception
    assert app.metric[2].value == "1"
    next(item for item in app.selectbox if item.label == "Status").select("unresolved").run()
    assert not app.exception
    assert app.radio[0].options[0].startswith("Q1")
    app.run()
    assert app.metric[2].value == "1"
    assert Store(tmp_path / "review.sqlite").attempt_count() == 0
