#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_EXTS = {".py", ".yml", ".yaml", ".toml", ".txt", ".md", ".cfg", ".ini"}

BANNED_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("pip_install", re.compile(r"(^|\s)pip\s+install\s+.*\bstegid\b", re.IGNORECASE)),
    ("import", re.compile(r"^\s*import\s+stegid\b", re.IGNORECASE)),
    ("from_import", re.compile(r"^\s*from\s+stegid\b", re.IGNORECASE)),
    ("repo_url", re.compile(r"stegverse-labs/StegID(\.git)?", re.IGNORECASE)),
]

def git_ls_files() -> List[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=str(REPO_ROOT), text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]

def should_scan(rel: str) -> bool:
    p = Path(rel)
    if p.suffix.lower() not in SCAN_EXTS:
        return False
    if ".git" in p.parts:
        return False
    if ".github" in p.parts:
        # avoid self-matching workflow text
        return False
    return True

def scan_file(rel: str) -> List[Tuple[str, int, str, str]]:
    p = REPO_ROOT / rel
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    hits: List[Tuple[str, int, str, str]] = []
    for i, line in enumerate(lines, start=1):
        for tag, pat in BANNED_PATTERNS:
            if pat.search(line):
                hits.append((rel, i, tag, line))
    return hits

def main() -> int:
    print("\n🔎 Scanning repo for forbidden external dependency usage...\n")
    files = [f for f in git_ls_files() if should_scan(f)]

    hits: List[Tuple[str, int, str, str]] = []
    for f in files:
        hits.extend(scan_file(f))

    if not hits:
        print("✅ Scan passed. No forbidden external dependency usage found.\n")
        return 0

    print("❌ Found forbidden external dependency usage:\n")
    for rel, ln, tag, line in hits:
        print(f"{rel}:{ln}: [{tag}] {line}")
    print("\nFix the lines above, then re-run.\n")
    return 1

if __name__ == "__main__":
    sys.exit(main())
