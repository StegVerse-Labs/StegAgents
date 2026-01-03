#!/usr/bin/env python3
"""
Path-stable shim. Workflows call scripts/scan_no_stegid.py forever.
The implementation may live in /archive (or later scripts/_impl).
"""
from __future__ import annotations

import runpy
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
impl_candidates = [
    REPO / "scripts" / "_impl" / "scan_no_stegid.py",
    REPO / "archive" / "scan_no_stegid.py",
]

target = next((p for p in impl_candidates if p.exists()), None)
if not target:
    print("ERROR: scan_no_stegid implementation not found.", file=sys.stderr)
    for p in impl_candidates:
        print(f" - {p}", file=sys.stderr)
    sys.exit(2)

runpy.run_path(str(target), run_name="__main__")
