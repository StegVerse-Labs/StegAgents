from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


def verify_receipt(
    receipt: Dict[str, Any],
    *,
    public_keys: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Minimal local receipt verifier.

    Returns:
      {"ok": True, "receipt": <receipt>} on success
      {"ok": False, "error": "..."} on failure
    """
    try:
        if not isinstance(receipt, dict):
            return {"ok": False, "error": "Receipt must be a dict"}

        issuer = receipt.get("issuer", "")
        if not issuer:
            return {"ok": False, "error": "Receipt missing issuer"}

        # Accept local receipts only (deterministic, no crypto here)
        if str(issuer).lower() != "local":
            return {"ok": False, "error": "Only local receipts are accepted in this repo"}

        receipt.setdefault("verified", True)
        receipt.setdefault("verifier", "local-receipt")

        return {"ok": True, "receipt": receipt}
    except Exception as e:
        return {"ok": False, "error": f"Receipt verification error: {e.__class__.__name__}: {e}"}


def load_receipt_from_env() -> Dict[str, Any]:
    """
    Load receipt JSON from env var:
      SV_RECEIPT_JSON
    """
    raw = (os.getenv("SV_RECEIPT_JSON") or "").strip()
    if not raw:
        return {"issuer": "local", "verified": True, "note": "No receipt provided; local default used"}

    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return {"issuer": "local", "verified": True, "note": "Receipt JSON was not an object; local default used"}
        return obj
    except Exception as e:
        return {"issuer": "local", "verified": True, "note": f"Invalid SV_RECEIPT_JSON; local default used ({e.__class__.__name__})"}
