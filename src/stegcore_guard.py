from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from stegcore import decide, Decision, ActionIntent, VerifiedReceipt


class StegCoreDenied(RuntimeError):
    def __init__(self, decision: Decision):
        super().__init__(f"DENIED_BY_STEGCORE: {decision.verdict} {decision.reason_code}")
        self.decision = decision


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_verified_receipt_from_env() -> Optional[VerifiedReceipt]:
    """
    Load verified receipt from:
      SV_RECEIPT_JSON
    """
    raw = os.getenv("SV_RECEIPT_JSON", "").strip()
    if not raw:
        return None

    obj = json.loads(raw)
    return VerifiedReceipt(
        receipt_id=obj["receipt_id"],
        actor_class=obj["actor_class"],
        scopes=list(obj.get("scopes", [])),
        issued_at=_parse_dt(obj["issued_at"]),
        expires_at=_parse_dt(obj["expires_at"]),
        assurance_level=int(obj.get("assurance_level", 0)),
        signals=list(obj.get("signals", [])),
        proof=obj.get("proof"),
    )


def require_allowed(
    *,
    receipt: Optional[VerifiedReceipt],
    action: str,
    resource: str,
    scope: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Decision:
    intent = ActionIntent(
        action=action,
        resource=resource,
        scope=scope,
        parameters=parameters or {},
    )

    d = decide(receipt, intent)
    if d.verdict != "ALLOW":
        raise StegCoreDenied(d)
    return d
