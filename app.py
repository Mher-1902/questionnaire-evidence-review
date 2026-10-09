"""Local review UI. All generated/source text is rendered as plain text."""

import difflib
import json
import os
from pathlib import Path

import streamlit as st

from evidence_review.domain import (
    Answer,
    Authority,
    Citation,
    load_dataset,
    source_changes,
    validate_evidence,
)
from evidence_review.provider import Provider
from evidence_review.settings import ROOT, Settings
from evidence_review.storage import Store
from evidence_review.workflow import Workflow

st.set_page_config(page_title="Evidence Review", page_icon="📖", layout="wide")
settings = Settings.load()
state_dir = Path(os.environ.get("APP_STATE_DIR", str(ROOT / ".runtime")))
store = Store(state_dir / "review.sqlite")
try:
    dataset_id, data = store.snapshot()
except ValueError:
    data = load_dataset((ROOT / "fixtures/questionnaire.json").read_bytes())
    store.import_dataset(data)
    dataset_id, data = store.snapshot()
workflow = Workflow(store, Provider(settings, store))

st.title("Evidence Review")
st.caption("Answer buyer questions with visible evidence, human approval, and current sources.")
counts = workflow.counts()
columns = st.columns(4)
for column, label, value in zip(
    columns,
    ["Questions", "Answered", "Unresolved / review", "Approved"],
    [counts["total"], counts["answered"], counts["unresolved"], counts["approved"]],
    strict=True,
):
    column.metric(label, value)
st.caption(
    "Approved is a subset of answered. Processing errors are separate: " + str(counts["errors"])
)

with st.sidebar:
    st.header("Questionnaire queue")
    status_filter = st.selectbox(
        "Status", ["all", "pending", "draft", "approved", "unresolved", "needs_review", "error"]
    )
    statuses = {q.id: workflow.status(q) for q in data.questions}
    questions = [
        q for q in data.questions if status_filter == "all" or statuses[q.id] == status_filter
    ]
    mode_label = st.selectbox(
        "Response source",
        ["Saved real responses", "Live Cohere"],
        index=0 if settings.default_mode == "replay" else 1,
    )
    mode = "replay" if mode_label == "Saved real responses" else "live"
    strategy_label = st.selectbox(
        "Evidence strategy",
        ["Retrieve relevant evidence", "All documents baseline"],
        index=0 if settings.default_strategy == "retrieval" else 1,
    )
    strategy = "retrieval" if strategy_label == "Retrieve relevant evidence" else "full_context"
    if mode == "live":
        st.caption("Provider calls use a persisted budget and an overall deadline.")
        if not settings.api_key.get_secret_value():
            st.warning("Live access needs MODEL_API_KEY. Saved responses remain available.")
    if st.button("Draft pending questions", type="primary"):
        pending = [q for q in data.questions if statuses[q.id] in {"pending", "error"}]
        progress = st.progress(0, text="Preparing drafts")
        results = []
        for index, question in enumerate(pending):
            result = workflow.ask(question.id, mode=mode, strategy=strategy)
            results.append({"question": question.id, "status": result["status"]})
            progress.progress((index + 1) / len(pending), text="Processed " + question.id)
        st.session_state["batch_results"] = results
        st.rerun()
    if "batch_results" in st.session_state:
        st.dataframe(st.session_state["batch_results"], hide_index=True, width="stretch")
    if not questions:
        st.info("No questions match this filter.")
        selected_id = None
    else:
        selected_id = st.radio(
            "Question",
            [q.id for q in questions],
            format_func=lambda qid: f"{qid} · {statuses[qid]}",
        )
    with st.expander("Import source update"):
        st.caption("Validated JSON only, maximum 64 KiB. Source changes preserve approval history.")
        uploaded = st.file_uploader("Questionnaire JSON", type=["json"])
        if st.button("Import update", disabled=uploaded is None):
            try:
                changes = store.import_dataset(load_dataset(uploaded.getvalue()))
                st.session_state["import_result"] = (
                    f"Imported update: {len(changes)} source changes."
                )
                st.rerun()
            except ValueError:
                st.error(
                    "Import rejected: check size, schema, IDs, references, and reviewer mapping."
                )
    with st.expander("Model and controls"):
        st.json(settings.public())
        st.caption("Live attempts used: " + str(store.attempt_count()))
        st.caption("Local reviewer labels are not verified identities.")

if message := st.session_state.get("import_result"):
    st.info(message)

if selected_id:
    question = data.question(selected_id)
    draft = store.latest_draft(question)
    approval = store.latest_approval(question)
    answer = Answer.model_validate_json(draft["payload"]) if draft else None
    left, centre, right = st.columns([1, 1.4, 1.4], gap="large")

    with left:
        st.subheader("Question")
        st.text(question.text)
        st.caption("Owner: " + data.owners[question.topic])
        st.caption("Status: " + workflow.status(question))
        if st.button("Answer / reuse", type="primary"):
            with st.spinner("Checking approved knowledge and evidence…"):
                result = workflow.ask(question.id, mode=mode, strategy=strategy)
                st.session_state["last_result"] = {
                    "question_id": question.id,
                    "status": result["status"],
                    "metadata": result["metadata"],
                }
            st.rerun()
        if st.button("Generate a new draft"):
            with st.spinner("Generating a new suggestion…"):
                result = workflow.ask(question.id, mode=mode, strategy=strategy, force=True)
                st.session_state["last_result"] = {
                    "question_id": question.id,
                    "status": result["status"],
                    "metadata": result["metadata"],
                }
            st.rerun()
        last_result = st.session_state.get("last_result")
        if last_result and last_result["question_id"] == question.id:
            metadata = last_result["metadata"]
            st.caption("Last request: " + metadata["origin"])
            st.caption("New provider attempts: " + str(metadata.get("provider_attempts", 0)))
        st.divider()
        note = st.text_area("Review note", key="note_" + question.id, max_chars=2000)
        if st.button("Leave unresolved with note"):
            if note.strip():
                workflow.leave_unresolved(question, note)
                st.rerun()
            else:
                st.warning("Explain what evidence or clarification is needed.")

    with centre:
        st.subheader("Draft and review")
        runs = store.runs(question)
        if runs and (error := runs[0]["metadata"].get("error")):
            st.error(error)
        if not answer:
            st.info("Request an answer to create a reviewable draft.")
        else:
            current_errors = validate_evidence(answer, data)
            st.caption("Suggestion source: " + draft["origin"] + " · " + draft["created"])
            st.text(answer.answer)
            if answer.note:
                st.text(answer.note)
            for error in current_errors:
                st.warning(error)
            if answer.answerability != "supported":
                st.warning(
                    "Insufficient or conflicting evidence: review with "
                    + data.owners[question.topic]
                )
            with st.form("edit_" + draft["id"]):
                edited = st.text_area("Answer wording", value=answer.answer, max_chars=4000)
                answerability = st.selectbox(
                    "Evidence decision",
                    ["supported", "unknown", "conflicted"],
                    index=["supported", "unknown", "conflicted"].index(answer.answerability),
                )
                passage_map = data.passage_map()
                selected_citations = st.multiselect(
                    "Supporting passages",
                    list(passage_map),
                    default=[c.passage_id for c in answer.citations if c.passage_id in passage_map],
                )
                quotes = {
                    passage_id: st.text_area(
                        "Exact quote: " + passage_id,
                        value=next(
                            (c.quote for c in answer.citations if c.passage_id == passage_id),
                            passage_map[passage_id][1].text[:2000],
                        ),
                        max_chars=2000,
                    )
                    for passage_id in selected_citations
                }
                if st.form_submit_button("Save edited draft"):
                    try:
                        updated = answer.model_copy(
                            update={
                                "answer": edited,
                                "answerability": answerability,
                                "citations": [
                                    Citation(passage_id=p, quote=quotes[p])
                                    for p in selected_citations
                                ],
                            }
                        )
                        store.save_draft(question, updated, store.snapshot()[0], "human-edit")
                        st.rerun()
                    except ValueError:
                        st.error(
                            "Check answer wording and evidence quotes. "
                            "Unknown answers need an explanation."
                        )
            reviewer = st.text_input("Local reviewer label", value="Local reviewer", max_chars=128)
            semantic = st.checkbox(
                "I checked that the current evidence supports every claim in this answer.",
                key="semantic_" + draft["id"] + dataset_id,
            )
            acknowledge = st.checkbox(
                "I inspected source changes and review concerns since the previous approval.",
                key="acknowledge_" + draft["id"] + dataset_id,
            )
            if st.button("Approve exact saved revision", disabled=not semantic):
                try:
                    store.approve(
                        draft["id"],
                        reviewer,
                        semantic_confirmed=semantic,
                        changes_confirmed=acknowledge,
                        expected_dataset_id=dataset_id,
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        if approval:
            st.divider()
            st.subheader("Approved library")
            st.caption("Needs review" if approval["stale"] else "Current approved wording")
            approved = Answer.model_validate_json(approval["payload"])
            st.text(approved.answer)
            st.caption("Reviewer: " + approval["reviewer"] + " · " + approval["created"])
            previous = store.dataset(approval["dataset_id"])
            for citation in approved.citations:
                document, _ = previous.passage_map()[citation.passage_id]
                st.caption(
                    citation.passage_id + " · approved source version " + str(document.version)
                )
                st.text(citation.quote)

    with right:
        st.subheader("Evidence card")
        st.caption(
            "References and quotations are checked automatically. Meaning requires human review."
        )
        if authority_issues := Authority(data).issues():
            for issue in authority_issues:
                st.warning(issue)
        changes = store.review_changes(approval["id"]) if approval and approval["stale"] else []
        if draft and not changes and not store.draft_fresh(draft):
            changes = [
                c
                for c in source_changes(store.dataset(draft["dataset_id"]), data)
                if c["kind"] != "date"
            ]
        if changes:
            st.warning(
                "Source changes require inspection, including evidence not originally cited."
            )
            for change in changes:
                with st.expander(change["document_id"] + " · " + change["kind"], expanded=True):
                    before = json.dumps(change["before"], indent=2, ensure_ascii=False).splitlines()
                    after = json.dumps(change["after"], indent=2, ensure_ascii=False).splitlines()
                    st.code(
                        "\n".join(
                            difflib.unified_diff(before, after, fromfile="before", tofile="after")
                        ),
                        language="diff",
                    )
        used_ids = set()
        if answer:
            used_ids = {c.passage_id for c in answer.citations}
            used_ids |= {p for conflict in answer.conflicts for p in conflict.passage_ids}
        used_docs = {data.passage_map()[p][0].id for p in used_ids if p in data.passage_map()}
        related = Authority(data).family(used_docs)
        evidence_tab, all_tab = st.tabs(["Used evidence and history", "All current sources"])
        for tab, document_ids in [(evidence_tab, related), (all_tab, set(data.document_map()))]:
            with tab:
                if not document_ids:
                    st.caption("No supporting evidence selected.")
                for document in data.documents:
                    if document.id not in document_ids:
                        continue
                    with st.expander(
                        document.id + " · v" + str(document.version) + " · " + document.status,
                        expanded=document.id in related,
                    ):
                        st.caption(
                            "Date: "
                            + str(document.date)
                            + " · replaces: "
                            + str(document.supersedes)
                        )
                        for passage in document.passages:
                            st.caption(passage.id)
                            st.text(passage.text)
        if runs:
            with st.expander("Generation and retrieval trace"):
                st.json(runs[0]["metadata"])

    with st.expander("Revision and activity history"):
        for revision in store.revisions(question):
            st.caption(revision["created"] + " · " + revision["origin"])
            st.text(Answer.model_validate_json(revision["payload"]).answer)
        for event in store.history(question):
            st.caption(event["created"] + " · " + event["kind"])
            st.json(json.loads(event["payload"]))
