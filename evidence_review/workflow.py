import time

from pydantic import ValidationError

from .domain import Answer, question_key, validate_evidence
from .provider import ProviderError


class Workflow:
    def __init__(self, store, provider):
        self.store = store
        self.provider = provider

    def ask(self, question_id, *, mode="replay", strategy="retrieval", force=False):
        started = time.perf_counter()
        dataset_id, data = self.store.snapshot()
        question = data.question(question_id)
        if not force and (approval := self.store.reusable(question)):
            metadata = {
                "origin": "approved_reuse",
                "provider_attempts": 0,
                "new_provider_usage": {"input_tokens": 0, "output_tokens": 0},
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "approval_id": approval["id"],
            }
            self.store.event(question, "approved_reuse", metadata)
            self.store.save_run(question, metadata)
            return {
                "status": "approved",
                "answer": Answer.model_validate_json(approval["payload"]),
                "metadata": metadata,
                "approval": approval,
            }
        metadata = {"origin": mode, "provider_attempts": 0, "new_provider_usage": None}
        try:
            text, metadata = self.provider.generate(data, question, mode=mode, strategy=strategy)
            answer = Answer.model_validate_json(text)
            errors = validate_evidence(answer, data)
            metadata |= {
                "structural_errors": errors,
                "source_dataset_id": dataset_id,
                "semantic_review": "not-performed-by-validator",
            }
            run_id = self.store.save_run(question, metadata)
            draft_id = self.store.save_draft(question, answer, dataset_id, mode, run_id)
            return {
                "status": "error"
                if errors
                else "draft"
                if answer.answerability == "supported"
                else "unresolved",
                "answer": answer,
                "draft_id": draft_id,
                "metadata": metadata,
            }
        except ProviderError as error:
            metadata = error.metadata | {"error_code": error.code, "error": str(error)}
        except (ValidationError, ValueError, TypeError, KeyError):
            metadata |= {
                "error_code": "invalid_model_output",
                "error": "Model output failed the application contract; no answer invented.",
            }
        metadata["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self.store.save_run(question, metadata)
        self.store.event(question, "processing_error", {"error_code": metadata["error_code"]})
        return {"status": "error", "metadata": metadata}

    def status(self, question):
        if self.store.reusable(question):
            return "approved"
        draft = self.store.latest_draft(question)
        approval = self.store.latest_approval(question)
        if approval and approval["stale"]:
            return "needs_review"
        runs = self.store.runs(question)
        if runs and runs[0]["metadata"].get("error"):
            if not draft or runs[0]["created"] > draft["created"]:
                return "error"
        if not draft:
            return "pending"
        answer = Answer.model_validate_json(draft["payload"])
        # An invalid original reference is an error, not a later source change.
        # Validate the immutable generation snapshot before checking freshness.
        if validate_evidence(answer, self.store.dataset(draft["dataset_id"])):
            return "error"
        if not self.store.draft_fresh(draft):
            return "needs_review"
        if validate_evidence(answer, self.store.snapshot()[1]):
            return "error"
        return "draft" if answer.answerability == "supported" else "unresolved"

    def counts(self):
        statuses = [self.status(q) for q in self.store.snapshot()[1].questions]
        return {
            "total": len(statuses),
            "answered": statuses.count("draft") + statuses.count("approved"),
            "unresolved": statuses.count("unresolved") + statuses.count("needs_review"),
            "approved": statuses.count("approved"),
            "errors": statuses.count("error"),
        }

    def leave_unresolved(self, question, note):
        if not note.strip():
            raise ValueError("Explain what evidence or clarification is needed")
        note = note[:2000]
        dataset_id, data = self.store.snapshot()
        draft = self.store.latest_draft(question)
        if draft:
            answer = Answer.model_validate_json(draft["payload"])
            answer = answer.model_copy(update={"answerability": "unknown", "note": note})
        else:
            answer = Answer(
                answer="",
                answerability="unknown",
                conflict_resolution="none",
                citations=[],
                conflicts=[],
                note=note,
            )
        self.store.save_draft(question, answer, dataset_id, "human-review")
        self.store.require_review(question, note)
        self.store.event(
            question,
            "review_note",
            {
                "note": note,
                "owner": data.owners[question.topic],
                "question_key": question_key(question),
            },
        )
