#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]

# What we scan (keep it small + relevant)
SCAN_EXTS = {".py", ".yml", ".yaml", ".toml", ".md", ".txt", ".json"}

# Paths we skip (avoid vendor noise)
SKIP_DIR_PARTS = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}

# If you have any paths that are allowed to reference StegID (rare),
# you can add explicit allowlist entries here.
ALLOWLIST_PATH_PREFIXES: Tuple[str, ...] = (
    # Example:
    # "docs/legacy/",
)

# Banned patterns (tuned to your “no external StegID dependency” intent)
BANNED_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    # Direct “StegID” name usage (common drift)
    ("stegid_word", re.compile(r"\bstegid\b", re.IGNORECASE)),
    ("steg_id_word", re.compile(r"\bsteg[_-]?id\b", re.IGNORECASE)),

    # GitHub repo references (canonical)
    ("stegid_repo_ref", re.compile(r"StegVerse[-_/]Labs/StegID", re.IGNORECASE)),

    # Import patterns (python)
    ("python_import_stegid", re.compile(r"^\s*import\s+steg[_-]?id\b", re.IGNORECASE | re.MULTILINE)),
    ("python_from_stegid", re.compile(r"^\s*from\s+steg[_-]?id\b", re.IGNORECASE | re.MULTILINE)),

    # Install patterns
    ("pip_install_stegid", re.compile(r"\bpip\s+install\b.*\bsteg[_-]?id\b", re.IGNORECASE)),
    ("requirements_stegid", re.compile(r"^\s*steg[_-]?id\b", re.IGNORECASE | re.MULTILINE)),

    # GitHub Actions “uses:” pulling StegID workflows/actions
    ("actions_uses_stegid", re.compile(r"uses:\s*StegVerse[-_/]Labs/StegID\b", re.IGNORECASE)),
]


def _git_ls_files() -> List[str]:
    """
    Prefer git-tracked files to avoid scanning artifacts.
    Falls back to walking the repo if git isn’t available.
    """
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=str(REPO_ROOT))
        files = [line.strip() for line in out.decode("utf-8", errors="ignore").splitlines() if line.strip()]
        return files
    except Exception:
        # Fallback: walk filesystem
        paths: List[str] = []
        for p in REPO_ROOT.rglob("*"):
            if p.is_file():
                paths.append(str(p.relative_to(REPO_ROOT)).replace("\\", "/"))
        return paths


def _should_skip(path: str) -> bool:
    # Allowlist takes precedence (explicit)
    for pref in ALLOWLIST_PATH_PREFIXES:
        if path.startswith(pref):
            return True

    parts = Path(path).parts
    for part in parts[:-1]:
        if part in SKIP_DIR_PARTS:
            return True
    return False


def _iter_scan_files() -> Iterable[str]:
    for rel in _git_ls_files():
        if _should_skip(rel):
            continue
        p = Path(rel)
        if p.suffix.lower() in SCAN_EXTS:
            yield rel


def _read_text(rel: str) -> str:
    fp = REPO_ROOT / rel
    try:
        return fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def main() -> int:
    hits: List[Tuple[str, str, int, str]] = []  # (file, rule, line_no, line)

    for rel in _iter_scan_files():
        text = _read_text(rel)
        if not text:
            continue

        # Fast reject: if no "steg" substring, skip regex cost
        if "steg" not in text.lower():
            continue

        # Check each banned pattern
        for rule, rx in BANNED_PATTERNS:
            for m in rx.finditer(text):
                # best-effort line extraction
                start = m.start()
                line_no = text.count("\n", 0, start) + 1
                line = text.splitlines()[line_no - 1] if text.splitlines() else ""
                hits.append((rel, rule, line_no, line.strip()))
                # Don’t spam: one hit per rule per file is enough
                break

    if hits:
        print("❌ ERROR: Forbidden StegID external dependency/reference detected.")
        print("These references must not exist in this repo.\n")
        for rel, rule, line_no, line in hits[:80]:
            print(f"- {rel}:{line_no}  [{rule}]  {line}")
        if len(hits) > 80:
            print(f"\n… plus {len(hits) - 80} more.")
        print("\nFix: remove the reference or explicitly allowlist a path (rare).")
        return 2

    print("✅ scan_no_stegid: OK (no forbidden references found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
