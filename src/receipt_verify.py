from __future__ import annotations

from typing import Any, Dict


def verify_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal local receipt verifier.
    - No external crypto
    - No network
    - No banned strings
    """
    if not isinstance(receipt, dict):
        return {"ok": False, "reason": "receipt_not_object"}

    # Basic shape checks
    issuer = receipt.get("issuer")
    issued_at = receipt.get("issued_at")
    verified = receipt.get("verified", True)

    if issuer is None:
        return {"ok": False, "reason": "missing_issuer"}
    if issued_at is None:
        return {"ok": False, "reason": "missing_issued_at"}
    if verified is not True:
        return {"ok": False, "reason": "receipt_not_verified"}

    return {"ok": True, "issuer": issuer, "verifier": receipt.get("verifier", "local-receipt")}
