#!/usr/bin/env bash
# Prepare the isolated environment, verify the demo, and start the local app.
set -Eeuo pipefail
umask 077

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UV_VERSION="0.12.24"
UV_LOCAL_BIN="$PROJECT_ROOT/.runtime/bootstrap/bin/uv"
UV_BIN=""
CHECK_ONLY=0
FORCE_BOOTSTRAP=0
LAUNCHER_PORT=8501

usage() {
  cat <<'USAGE'
Usage: ./full_run.sh [--check-only] [--port NUMBER] [--bootstrap]

Default: install the pinned Python/environment and locked packages, run lint,
tests and real-response replay checks, then start the app on localhost:8501.
No API key is needed. Initial setup needs Internet and curl or wget.

  --check-only  Complete setup and verification without starting the server.
  --port        Choose another localhost port (for example, 8502).
  --bootstrap   Use the project-local pinned uv, even if uv is installed globally.
  --help        Show this help without changing anything.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only) CHECK_ONLY=1; shift ;;
    --bootstrap) FORCE_BOOTSTRAP=1; shift ;;
    --port)
      if [ "$#" -lt 2 ]; then printf 'Missing value for --port.\n' >&2; exit 2; fi
      LAUNCHER_PORT="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! "$LAUNCHER_PORT" =~ ^[0-9]{1,5}$ ]] ||
   (( 10#$LAUNCHER_PORT < 1024 || 10#$LAUNCHER_PORT > 65535 )); then
  printf 'Choose a port between 1024 and 65535.\n' >&2
  exit 2
fi
case "$(uname -s)" in
  Darwin|Linux) ;;
  *) printf 'Use macOS, Linux, or Windows through WSL for this launcher.\n' >&2; exit 2 ;;
esac

cd -- "$PROJECT_ROOT"
trap 'printf "Setup stopped at line %s. Fix the reported error and rerun; the app was not started.\n" "$LINENO" >&2' ERR
export UV_CACHE_DIR="$PROJECT_ROOT/.runtime/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/.runtime/python"
export UV_PROJECT_ENVIRONMENT="$PROJECT_ROOT/.venv"

is_pinned_uv() {
  [ -x "$1" ] || return 1
  local reported
  reported="$("$1" --version)"
  [[ "$reported" == "uv $UV_VERSION" || "$reported" == "uv $UV_VERSION "* ]]
}

printf '\n[1/4] Locate or install uv %s (project-local bootstrap).\n' "$UV_VERSION"
if is_pinned_uv "$UV_LOCAL_BIN"; then
  UV_BIN="$UV_LOCAL_BIN"
elif [ "$FORCE_BOOTSTRAP" -eq 0 ]; then
  for candidate in "$(command -v uv || true)" /opt/homebrew/bin/uv /usr/local/bin/uv; do
    if [ -n "$candidate" ] && is_pinned_uv "$candidate"; then UV_BIN="$candidate"; break; fi
  done
fi
if [ -z "$UV_BIN" ]; then
  mkdir -p -- "$PROJECT_ROOT/.runtime/bootstrap"
  installer="$PROJECT_ROOT/.runtime/bootstrap/install-uv-$UV_VERSION.sh"
  installer_url="https://astral.sh/uv/$UV_VERSION/install.sh"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --retry 2 --connect-timeout 10 --max-time 90 \
      "$installer_url" --output "$installer"
  elif command -v wget >/dev/null 2>&1; then
    wget --quiet --timeout=30 --tries=3 --output-document="$installer" "$installer_url"
  else
    printf 'Install curl or wget, then rerun this command.\n' >&2
    exit 1
  fi
  UV_UNMANAGED_INSTALL="$PROJECT_ROOT/.runtime/bootstrap/bin" sh "$installer"
  UV_BIN="$UV_LOCAL_BIN"
  if ! is_pinned_uv "$UV_BIN"; then printf 'Pinned uv bootstrap did not succeed.\n' >&2; exit 1; fi
fi

printf '\n[2/4] Prepare Python and .venv; install locked runtime and development packages.\n'
"$UV_BIN" sync --locked --python "$(cat .python-version)"

printf '\n[3/4] Run lint, tests, and keyless real-response verification.\n'
"$UV_BIN" run --no-sync ruff check .
"$UV_BIN" run --no-sync ruff format --check .
"$UV_BIN" run --no-sync pytest
"$UV_BIN" run --no-sync python scripts/verify.py

if [ "$CHECK_ONLY" -eq 1 ]; then
  printf '\nSetup and verification passed. No server or live model call was started.\n'
  exit 0
fi

printf '\n[4/4] Open http://127.0.0.1:%s — saved-response replay is the default.\n' "$LAUNCHER_PORT"
printf 'Press Ctrl+C to stop. The saved review database is preserved.\n'
exec "$UV_BIN" run --no-sync streamlit run app.py \
  --server.address=127.0.0.1 --server.port="$LAUNCHER_PORT"
