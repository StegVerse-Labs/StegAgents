from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# What we consider "lingering" references
NEEDLES = [
    "import stegid",
    "from stegid",
    "stegid.",
    "StegID",
    "stegverse-labs/StegID",
    "stegverse-labs/StegID.git",
]

# Where to search
INCLUDE_EXTS = {".py", ".yml", ".yaml", ".md", ".toml", ".txt", ".ini", ".cfg", ".lock"}

# Ignore noisy / irrelevant dirs
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".eggs",
    ".tox",
}

def should_scan(path: Path) -> bool:
    if path.is_dir():
        return False
    if path.suffix.lower() not in INCLUDE_EXTS:
        return False
    # Skip anything inside skip dirs
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return False
    return True

def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    hits = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        for needle in NEEDLES:
            if needle in line:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
                break
    return hits

def main() -> int:
    all_hits: list[str] = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # prune dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            p = Path(root) / fn
            if should_scan(p):
                all_hits.extend(scan_file(p))

    if all_hits:
        print("❌ Found lingering StegID/stegid references:\n")
        for h in all_hits:
            print(h)
        print("\nFix these references (use local src/stegid_receipts.py and remove stegid imports).")
        return 1

    print("✅ No lingering StegID/stegid references found.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
