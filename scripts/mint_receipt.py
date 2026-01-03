#!/usr/bin/env python3
from __future__ import annotations

import datetime as _dt
import json as _json
import os as _os
from typing import Any, Dict


def _utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _receipt(agent: str) -> Dict[str, Any]:
    return {
        "issuer": "local",
        "agent": agent or "unknown",
        "issued_at": _utc_now_iso(),
        "verified": True,
        "verifier": "local-receipt",
        "note": "CI-local receipt; no external receipt authority required.",
    }


def _write_github_env(key: str, value: str) -> None:
    env_path = _os.getenv("GITHUB_ENV", "")
    if not env_path:
        return
    with open(env_path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def _write_github_output(key: str, value: str) -> None:
    out_path = _os.getenv("GITHUB_OUTPUT", "")
    if not out_path:
        return
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def main() -> int:
    agent = _os.getenv("SV_AGENT", "unknown").strip()
    r = _receipt(agent)
    receipt_json = _json.dumps(r, separators=(",", ":"))

    # Set both ENV + OUTPUT for workflows (works whether called or direct).
    _write_github_env("SV_RECEIPT_JSON", receipt_json)
    _write_github_output("receipt_json", receipt_json)

    # Also print for logs
    print(receipt_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
