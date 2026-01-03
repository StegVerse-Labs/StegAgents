#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files we are allowed to mention StegID in (scanner + receipts only)
ALLOWLIST_PATHS = {
    "scripts/scan_no_stegid.py",
    "archives/scan_no_stegid.py",
    "src/sv_receipts.py",
}

SCAN_EXTS = {".py", ".yml", ".yaml", ".toml", ".md"}

BANNED_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    (
        "stegid_import",
        re.compile(r"^\s*(from|import)\s+stegid\b", re.IGNORECASE),
    ),
    (
        "stegid_repo",
        re.compile(r"stegverse-labs/stegid(\.git)?", re.IGNORECASE),
    ),
)


def git_ls_files() -> Iterable[str]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return (line.strip() for line in out.splitlines())


def should_scan(path: Path) -> bool:
    if path.suffix not in SCAN_EXTS:
        return False
    if path.as_posix() in ALLOWLIST_PATHS:
        return False
    return True


def main() -> int:
    violations = []

    for rel in git_ls_files():
        path = Path(rel)
        if not should_scan(path):
            continue

        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        for label, pattern in BANNED_PATTERNS:
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    violations.append(
                        f"- {rel}:{idx} [{label}] {line.strip()}"
                    )

    if violations:
        print("❌ ERROR: Forbidden StegID reference detected.\n")
        print("These references must not exist in this repo:\n")
        print("\n".join(violations))
        print("\nFix: remove the reference or explicitly allowlist the path.")
        return 2

    print("✅ Scan passed: no forbidden StegID references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
