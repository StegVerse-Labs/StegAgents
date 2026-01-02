#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _git_ls_files(root: Path) -> List[str]:
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=str(root), text=True)
        files = [line.strip() for line in out.splitlines() if line.strip()]
        return files
    except Exception:
        return []

def _build_banned_terms() -> List[str]:
    # Build terms without embedding the contiguous banned substrings in this file.
    lower = "".join(list("stegid"))
    mixed = "".join(["S", "t", "e", "g", "I", "D"])
    url = "".join(["stegverse", "-", "labs", "/", "Steg", "ID"])
    giturl = url + ".git"
    return [lower, mixed, url, giturl]

def _scan_text(path: Path, text: str, banned: List[str]) -> List[Tuple[str, int, str]]:
    hits: List[Tuple[str, int, str]] = []
    # case-insensitive match for any banned term
    pattern = re.compile("|".join(re.escape(t) for t in banned), re.IGNORECASE)
    for i, line in enumerate(text.splitlines(), start=1):
        m = pattern.search(line)
        if m:
            hits.append((str(path), i, line.rstrip("\n")))
    return hits

def main() -> int:
    root = _repo_root()
    print("\n🔎 Scanning repo for banned references...\n")
    print(f"📁 Repo root: {root}\n")

    files = _git_ls_files(root)
    if files:
        print(f"✅ Using git ls-files ({len(files)} tracked files).\n")
        paths = [root / f for f in files]
    else:
        # fallback: scan everything, but skip .git
        print("⚠️ git ls-files unavailable; falling back to filesystem walk.\n")
        paths = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]

    banned = _build_banned_terms()

    all_hits: List[Tuple[str, int, str]] = []
    for p in paths:
        # read as text best-effort
        try:
            data = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        all_hits.extend(_scan_text(p, data, banned))

    if all_hits:
        print("\n❌ Found banned references:\n")
        last_file = None
        for f, line_no, line in all_hits:
            if f != last_file:
                print(f"\n--- {os.path.relpath(f, str(root))} ---\n")
                last_file = f
            # show trimmed line
            show = line.strip()
            if len(show) > 240:
                show = show[:240] + "…"
            print(f"{os.path.relpath(f, str(root))}:{line_no}: {show}")
        print("\nFix the lines above, then re-run.\n")
        return 1

    print("✅ Scan clean. No banned references found.\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
