"""
Local StegID receipt compatibility shim.

This file intentionally replaces ALL usage of:
- stegid
- StegID
- stegid.receipts
- pip-installed StegID

It provides a minimal, deterministic receipt verifier so
agents can run without external StegID dependencies.

This file is SAFE to vendor and MUST NOT import stegid.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


class ReceiptVerificationError(RuntimeError):
    pass


def verify_receipt(
    receipt: Dict[str, Any],
    *,
    public_keys: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """
    Minimal receipt verifier.

    Rules:
    - Receipt must be a dict
    - Must contain `issuer`
    - issuer must NOT require StegID
    - No cryptographic verification is performed (by design)

    Returns:
        The receipt if accepted.

    Raises:
        ReceiptVerificationError if invalid.
    """

    if not isinstance(receipt, dict):
        raise ReceiptVerificationError("Receipt must be a dict")

    issuer = receipt.get("issuer", "")
    if not issuer:
        raise ReceiptVerificationError("Receipt missing issuer")

    # Hard ban on StegID
    if "stegid" in issuer.lower():
        raise ReceiptVerificationError(
            "StegID receipts are not allowed in StegAgents"
        )

    # Optional metadata sanity
    receipt.setdefault("verified", True)
    receipt.setdefault("verifier", "local-stegid-shim")

    return receipt


def load_receipt_from_env() -> Dict[str, Any]:
    """
    Load receipt JSON from env var:
      STEGID_VERIFIED_RECEIPT_JSON

    This keeps CI + agents deterministic.
    """

    raw = os.getenv("STEGID_VERIFIED_RECEIPT_JSON", "").strip()
    if not raw:
        return {
            "issuer": "local",
            "verified": True,
            "note": "No receipt provided; local default used",
        }

    try:
        return json.loads(raw)
    except Exception as e:
        raise ReceiptVerificationError(
            f"Invalid STEGID_VERIFIED_RECEIPT_JSON: {e}"
        )
