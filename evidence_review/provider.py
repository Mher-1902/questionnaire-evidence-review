"""Only this adapter has provider access. Recordings never include auth headers."""

import asyncio
import json
import os
import threading
import time
from pathlib import Path

import httpx

from .domain import Authority, canonical, digest
from .retrieval import retrieve
from .settings import ROOT, Settings

LIVE_LOCK = threading.Lock()
ENDPOINT = "https://api.cohere.com/v2/chat"


class ProviderError(Exception):
    def __init__(self, code, message, metadata=None):
        super().__init__(message)
        self.code = code
        self.metadata = metadata or {}


def build_request(data, question, settings: Settings, strategy):
    documents, trace = retrieve(data, question, strategy, settings.top_k)
    prompt = (ROOT / "prompts/system.md").read_text()
    schema = json.loads((ROOT / "prompts/answer-schema.json").read_text())
    prompt += "\nRequired JSON output contract:\n" + canonical(schema)
    authority = Authority(data)
    envelope = {
        "question": question.model_dump(),
        "documents": documents,
        "application_computed_authority": {
            "current_document_by_id": {d.id: authority.current(d.id) for d in data.documents},
            "issues": authority.issues(),
        },
        "context_strategy": strategy,
    }
    request = {
        "model": settings.model_id,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": canonical(envelope)},
        ],
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    if settings.output_format == "json_schema":
        request["response_format"]["schema"] = schema
    if settings.model_id.startswith("command-a-plus-"):
        request["thinking"] = {"type": settings.thinking}
    fingerprint = digest(request)
    trace |= {
        "prompt_version": digest(prompt),
        "schema_version": digest(schema),
        "request_fingerprint": fingerprint,
        "model_id": settings.model_id,
        "settings": settings.public(),
    }
    return request, trace


class Provider:
    def __init__(self, settings, store, recordings=None, transport=None):
        self.settings = settings
        self.store = store
        self.recordings = Path(recordings or ROOT / "replays")
        self.transport = transport

    def generate(self, data, question, *, mode="replay", strategy="retrieval"):
        started = time.perf_counter()
        request, trace = build_request(data, question, self.settings, strategy)
        trace |= {"origin": mode, "provider_attempts": 0, "new_provider_usage": None}
        fingerprint = trace["request_fingerprint"]
        target = self.recordings / f"{fingerprint}-{time.time_ns()}.json"
        if mode == "replay":
            candidates = list(self.recordings.glob(f"{fingerprint}*.json"))
            if not candidates:
                raise ProviderError(
                    "replay_missing", "No matching real recording; no live call made.", trace
                )
            target = max(
                candidates, key=lambda p: int(p.stem.split("-")[-1]) if "-" in p.stem else 0
            )
            saved = json.loads(target.read_text())
            if saved.get("kind") != "real-provider-response" or saved.get("request") != request:
                raise ProviderError(
                    "replay_mismatch", "Recording does not match this request.", trace
                )
            raw = saved["response"]
            if not isinstance(raw, dict):
                raise ProviderError(
                    "invalid_provider_response",
                    "Provider returned an invalid JSON envelope.",
                    trace,
                )
            trace |= {
                "recording": target.name,
                "recorded_usage": raw.get("usage"),
                "new_provider_usage": {"input_tokens": 0, "output_tokens": 0},
                "recorded_elapsed_ms": saved["metadata"]["elapsed_ms"],
            }
        elif mode == "live":
            if not self.settings.api_key.get_secret_value():
                raise ProviderError("key_missing", "Live generation requires MODEL_API_KEY.", trace)
            if not LIVE_LOCK.acquire(blocking=False):
                raise ProviderError(
                    "busy", "Another provider request is already in progress.", trace
                )
            try:
                raw = asyncio.run(self._request(request, trace))
            finally:
                LIVE_LOCK.release()
            if self.settings.api_key.get_secret_value() in canonical(raw):
                raise ProviderError(
                    "secret_echo", "Credential-bearing response rejected; not saved.", trace
                )
            trace |= {"new_provider_usage": raw.get("usage"), "recording": target.name}
            trace["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
            self.recordings.mkdir(parents=True, exist_ok=True)
            saved = {
                "kind": "real-provider-response",
                "request": request,
                "response": raw,
                "metadata": trace,
            }
            # Authorization and credentials are intentionally never part of request/saved.
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n")
            os.replace(temporary, target)
        else:
            raise ValueError("Unknown provider mode")
        trace["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        if str(raw.get("finish_reason", "")).lower() != "complete":
            raise ProviderError(
                "incomplete", "Provider response did not complete; draft rejected.", trace
            )
        message = raw.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if (
            not isinstance(content, list)
            or not content
            or any(
                not isinstance(part, dict)
                or part.get("type") != "text"
                or not isinstance(part.get("text"), str)
                or not part["text"].strip()
                for part in content
            )
        ):
            raise ProviderError(
                "invalid_provider_response",
                "Provider returned invalid content for a text-only draft; no answer invented.",
                trace,
            )
        return "".join(part["text"] for part in content), trace

    async def _request(self, request, trace):
        started = time.monotonic()
        try:
            async with asyncio.timeout(self.settings.deadline_seconds):
                for attempt in range(self.settings.max_retries + 1):
                    remaining = self.settings.deadline_seconds - (time.monotonic() - started)
                    try:
                        self.store.reserve_attempt(
                            self.settings.attempt_budget, self.settings.attempts_per_minute
                        )
                    except ValueError as error:
                        raise ProviderError("local_limit", str(error), trace) from None
                    trace["provider_attempts"] += 1
                    try:
                        async with httpx.AsyncClient(
                            timeout=httpx.Timeout(remaining, connect=min(5, remaining)),
                            transport=self.transport,
                            follow_redirects=False,
                        ) as client:
                            response = await client.post(
                                ENDPOINT,
                                json=request,
                                headers={
                                    "Authorization": "Bearer "
                                    + self.settings.api_key.get_secret_value()
                                },
                            )
                    except httpx.HTTPError:
                        if attempt == self.settings.max_retries:
                            raise ProviderError(
                                "network", "Provider network request failed.", trace
                            ) from None
                        await asyncio.sleep(min(2**attempt, remaining))
                        continue
                    trace["http_status"] = response.status_code
                    if response.status_code == 200:
                        try:
                            raw = response.json()
                            if not isinstance(raw, dict):
                                raise ValueError
                            return raw
                        except (ValueError, TypeError):
                            raise ProviderError(
                                "invalid_provider_response",
                                "Provider returned an invalid JSON envelope.",
                                trace,
                            ) from None
                    if response.status_code in {401, 403, 498}:
                        raise ProviderError(
                            "authentication", "Provider authentication/access failed.", trace
                        )
                    if response.status_code == 404:
                        raise ProviderError(
                            "model_unavailable", "Configured model is unavailable.", trace
                        )
                    if response.status_code not in {429, 500, 502, 503, 504}:
                        detail = "Request rejected"
                        try:
                            message = response.json().get("message")
                            if isinstance(message, str):
                                detail = message.replace(
                                    self.settings.api_key.get_secret_value(), "[redacted]"
                                )[:500]
                        except (ValueError, AttributeError):
                            pass
                        raise ProviderError(
                            "request_rejected",
                            f"Provider HTTP {response.status_code}: {detail}",
                            trace,
                        )
                    if attempt == self.settings.max_retries:
                        raise ProviderError(
                            "provider_unavailable", "Provider retry limit reached.", trace
                        )
                    try:
                        wait = max(0, float(response.headers.get("Retry-After", 2**attempt)))
                    except ValueError:
                        wait = 2**attempt
                    await asyncio.sleep(wait)
        except TimeoutError:
            raise ProviderError(
                "deadline", "Overall generation deadline exceeded.", trace
            ) from None
        raise ProviderError("provider_unavailable", "Provider request failed.", trace)
