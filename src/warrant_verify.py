import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nacl.signing import VerifyKey


def _parse_dt(s: str) -> datetime:
    # Accept "Z"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_payload(warrant: Dict[str, Any]) -> bytes:
    w = dict(warrant)
    w.pop("signature", None)
    return json.dumps(w, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class WarrantDecision:
    ok: bool
    reason: str
    payload_sha256: Optional[str] = None


def verify_warrant(
    warrant: Dict[str, Any],
    issuer_pubkey_b64: str,
    expected_bundle_sha256: str,
    observed_repo: str,
    observed_commit_sha: str,
    max_ttl_seconds: int = 900,
) -> WarrantDecision:
    try:
        sig = warrant.get("signature") or {}
        alg = sig.get("alg")
        if alg != "ed25519":
            return WarrantDecision(False, f"Unsupported signature alg: {alg}")

        issued_at = _parse_dt(warrant["issued_at"])
        expires_at = _parse_dt(warrant["expires_at"])
        now = _utc_now()

        if expires_at <= now:
            return WarrantDecision(False, "Warrant expired.")
        if issued_at > now:
            return WarrantDecision(False, "Warrant issued in the future (clock skew).")

        ttl = (expires_at - issued_at).total_seconds()
        if ttl > max_ttl_seconds:
            return WarrantDecision(False, f"TTL too long: {ttl}s > {max_ttl_seconds}s")

        policy = warrant.get("policy") or {}
        bundle_sha = (policy.get("bundle_sha256") or "").lower()
        if not bundle_sha or bundle_sha != expected_bundle_sha256.lower():
            return WarrantDecision(False, "Policy bundle hash mismatch (pinning failed).")

        claims = warrant.get("claims") or {}
        w_repo = (claims.get("repo") or "").lower()
        w_sha = (claims.get("commit_sha") or "").lower()
        if w_repo != observed_repo.lower():
            return WarrantDecision(False, "Repo claim mismatch.")
        if w_sha != observed_commit_sha.lower():
            return WarrantDecision(False, "Commit claim mismatch.")

        payload = _canonical_payload(warrant)
        payload_sha = _sha256_hex(payload)

        sig_b64 = sig.get("sig_b64") or ""
        sig_bytes = base64.b64decode(sig_b64)

        pub = base64.b64decode(issuer_pubkey_b64.strip())
        vk = VerifyKey(pub)
        vk.verify(payload, sig_bytes)

        return WarrantDecision(True, "OK", payload_sha256=payload_sha)
    except Exception as e:
        return WarrantDecision(False, f"Verification error: {e}")
