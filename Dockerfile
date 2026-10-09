FROM python:3.12.15-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
COPY --from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_STATE_DIR=/app/.runtime
COPY pyproject.toml uv.lock .python-version ./
COPY evidence_review ./evidence_review
RUN uv sync --locked --no-dev

# Explicit allowlist: no .env, local database, Git credentials, or personal configuration.
COPY app.py app-config.toml README.md ./
COPY .streamlit ./.streamlit
COPY prompts ./prompts
COPY fixtures ./fixtures
COPY replays ./replays
COPY docs ./docs
COPY scripts ./scripts
COPY client-ai-starter-pack/tasks/evidence ./client-ai-starter-pack/tasks/evidence
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /app/.runtime /app/reports && chown -R app:app /app
USER app
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2).read()"]
CMD ["uv", "run", "--no-sync", "streamlit", "run", "app.py", "--server.address=0.0.0.0"]
