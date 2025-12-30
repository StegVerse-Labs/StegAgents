from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple


def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    # ISO8601 with Z
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_json(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Receipt:
    # Top-level fields your existing agent_runner expects
    receipt_id: str
    actor_class: str
    scopes: List[str]
    issued_at: str
    expires_at: str
    assurance_level: int
    signals: List[str]

    # Proof
    issuer: str
    kid: str
    payload_hash: str
    sig: str

    # Embedded payload for verification
    payload: dict

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "actor_class": self.actor_class,
            "scopes": self.scopes,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "assurance_level": self.assurance_level,
            "signals": self.signals,
            "issuer": self.issuer,
            "kid": self.kid,
            "payload_hash": self.payload_hash,
            "sig": self.sig,
            "payload": self.payload,
        }


def mint_receipt(
    priv_b64: str,
    actor_class: str,
    scopes: List[str],
    ttl_seconds: int,
    assurance_level: int = 1,
    signals: Optional[List[str]] = None,
    issuer: str = "stegid",
    kid: str = "local-ed25519-1",
) -> Receipt:
    """
    Minimal StegID-compatible receipt minting:
    - Ed25519 signature over canonical JSON of payload.
    - payload_hash is sha256 hex of canonical payload.
    - Signature is base64url (no padding).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except Exception as e:
        raise RuntimeError(
            "cryptography is required for receipt minting. Add 'cryptography' to requirements.txt."
        ) from e

    signals = signals or []
    now = _utc_now()
    exp = now + timedelta(seconds=int(ttl_seconds))

    payload = {
        "receipt_id": str(uuid.uuid4()),
        "issuer": issuer,
        "kid": kid,
        "actor_class": actor_class,
        "scopes": list(scopes),
        "issued_at": _iso(now),
        "expires_at": _iso(exp),
        "assurance_level": int(assurance_level),
        "signals": list(signals),
    }

    payload_bytes = _canonical_json(payload)
    payload_hash = _sha256_hex(payload_bytes)

    priv = Ed25519PrivateKey.from_private_bytes(_b64u_decode(priv_b64.strip()))
    sig = priv.sign(payload_bytes)

    return Receipt(
        receipt_id=payload["receipt_id"],
        actor_class=payload["actor_class"],
        scopes=payload["scopes"],
        issued_at=payload["issued_at"],
        expires_at=payload["expires_at"],
        assurance_level=payload["assurance_level"],
        signals=payload["signals"],
        issuer=issuer,
        kid=kid,
        payload_hash=payload_hash,
        sig=_b64u_encode(sig),
        payload=payload,
    )


def verify_receipt(receipt: dict, pubkeys_by_kid: Dict[str, str]) -> Tuple[bool, str]:
    """
    Verify the receipt signature using Ed25519.
    Returns (ok, reason).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except Exception as e:
        return False, "NO_CRYPTOGRAPHY"

    kid = (receipt.get("kid") or "").strip()
    sig_b64 = (receipt.get("sig") or "").strip()
    payload = receipt.get("payload")

    if not kid:
        return False, "MISSING_KID"
    if not sig_b64:
        return False, "MISSING_SIG"
    if not isinstance(payload, dict):
        return False, "MISSING_PAYLOAD"

    pub_b64 = (pubkeys_by_kid.get(kid) or "").strip()
    if not pub_b64:
        return False, "UNKNOWN_KID"

    payload_bytes = _canonical_json(payload)

    # Check payload_hash matches
    expected_hash = _sha256_hex(payload_bytes)
    if (receipt.get("payload_hash") or "") != expected_hash:
        return False, "PAYLOAD_HASH_MISMATCH"

    # Check expiry basic sanity (optional, but good guardrail)
    expires_at = payload.get("expires_at", "")
    if expires_at:
        try:
            exp = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if _utc_now() > exp:
                return False, "EXPIRED"
        except Exception:
            return False, "BAD_EXPIRES_AT"

    try:
        pub = Ed25519PublicKey.from_public_bytes(_b64u_decode(pub_b64))
        pub.verify(_b64u_decode(sig_b64), payload_bytes)
    except Exception:
        return False, "BAD_SIGNATURE"

    return True, "OK"
