"""Deliver only tracked, allowed source/configuration and sanitized replay inputs."""

import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIRS = {
    "evidence_review",
    "prompts",
    "fixtures",
    "replays",
    "docs",
    "scripts",
    "ai-workflow",
    ".streamlit",
    "client-ai-starter-pack",
    "tests",
    ".github",
}
ALLOWED_FILES = {
    "full_run.sh",
    "app.py",
    "app-config.toml",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".env.example",
    "README.md",
    "AGENTS.md",
    "Dockerfile",
    ".dockerignore",
    "compose.yaml",
    ".gitignore",
}


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    target = output / f"review-demo-{commit}.tar.gz"
    files = []
    with tarfile.open(target, "w:gz") as archive:
        for filename in tracked:
            if not filename:
                continue
            path = Path(filename)
            allowed = filename in ALLOWED_FILES or path.parts[0] in ALLOWED_DIRS
            if (
                not allowed
                or path.is_absolute()
                or ".." in path.parts
                or ROOT.joinpath(path).is_symlink()
            ):
                continue
            if path.name.startswith(".env") and filename != ".env.example":
                continue
            archive.add(ROOT / path, arcname="review-demo/" + filename, recursive=False)
            files.append(filename)
        for filename in ["reports/verification.json", "reports/verification.md"]:
            archive.add(ROOT / filename, arcname="review-demo/" + filename, recursive=False)
    (output / "delivery-manifest.json").write_text(
        json.dumps(
            {
                "commit": commit,
                "archive": target.name,
                "files": files,
                "scope": "Local container/source delivery; no cloud deployment",
            },
            indent=2,
        )
        + "\n"
    )
    print(target.name)


if __name__ == "__main__":
    main()
