from streamlit.testing.v1 import AppTest

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
