#!/usr/bin/env python3
"""
Scan repo for banned StegID/stegid references and print exact file:line hits.

- Prints all matches with file path + line number + the matched line.
- Excludes ONLY this scanner script + the scan workflow file to prevent self-matches.
- Scans tracked files via `git ls-files` when available (best), otherwise falls back to walking the tree.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


BANNED_REGEXES: List[Tuple[str, re.Pattern]] = [
    ("stegid (word)", re.compile(r"(?i)\bstegid\b")),
    ("StegID (word)", re.compile(r"\bStegID\b")),
    ("stegverse-labs/StegID", re.compile(r"(?i)stegverse-labs/StegID")),
    ("StegID.git", re.compile(r"(?i)StegID\.git")),
    ("import stegid", re.compile(r"(?i)^\s*import\s+stegid\b")),
    ("from stegid", re.compile(r"(?i)^\s*from\s+stegid\b")),
]

# Files to exclude so the scan doesn't fail because it sees its own patterns.
EXCLUDE_PATHS = {
    "scripts/scan_no_stegid.py",
    ".github/workflows/scan-and-run.yml",
}

# Directories to ignore for walk fallback
IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "out", ".mypy_cache", ".pytest_cache", "node_modules"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_text_file(path: Path) -> bool:
    # Quick heuristic: try read as utf-8 with replacement
    try:
        _ = path.read_text(encoding="utf-8", errors="strict")
        return True
    except Exception:
        try:
            _ = path.read_text(encoding="utf-8", errors="replace")
            return True
        except Exception:
            return False


def git_tracked_files(root: Path) -> List[Path]:
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=str(root), text=True)
        files = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            files.append(root / line)
        return files
    except Exception:
        return []


def walk_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            files.append(p)
    return files


def relpath(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except Exception:
        return p.as_posix()


def scan_file(root: Path, p: Path) -> List[Tuple[str, int, str, str]]:
    """
    Returns list of (relpath, line_no, rule_name, line_text)
    """
    rp = relpath(root, p)
    if rp in EXCLUDE_PATHS:
        return []

    # Skip obviously huge/binary-ish files
    if not is_text_file(p):
        return []

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    hits: List[Tuple[str, int, str, str]] = []
    for i, line in enumerate(lines, start=1):
        for rule_name, rx in BANNED_REGEXES:
            if rx.search(line):
                hits.append((rp, i, rule_name, line.rstrip("\n")))
    return hits


def main() -> int:
    root = repo_root()

    print("🔎 Scanning repo for banned StegID/stegid references...")
    print(f"📁 Repo root: {root}")

    files = git_tracked_files(root)
    if files:
        print(f"✅ Using git ls-files ({len(files)} tracked files).")
    else:
        files = walk_files(root)
        print(f"⚠️  git not available; walking tree ({len(files)} files found).")

    all_hits: List[Tuple[str, int, str, str]] = []

    for p in files:
        if not p.exists() or not p.is_file():
            continue
        all_hits.extend(scan_file(root, p))

    if not all_hits:
        print("✅ No banned StegID/stegid references found.")
        return 0

    print("\n❌ Found banned StegID/stegid references:\n")
    # Group by file for readability
    all_hits.sort(key=lambda x: (x[0], x[1], x[2]))
    current = None
    for rp, line_no, rule, line in all_hits:
        if rp != current:
            current = rp
            print(f"--- {rp} ---")
        print(f"{rp}:{line_no}: [{rule}] {line}")

    print("\nFix the lines above, then re-run the workflow.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
