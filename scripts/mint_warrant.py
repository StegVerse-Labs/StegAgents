import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from nacl.signing import SigningKey


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_payload(warrant: dict) -> bytes:
    # Signature covers everything except signature itself.
    w = dict(warrant)
    w.pop("signature", None)
    return json.dumps(w, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    issuer = os.environ["WARRANT_ISSUER"].strip()
    public_key_id = os.environ["WARRANT_PUBLIC_KEY_ID"].strip()
    priv_b64 = os.environ["WARRANT_ED25519_PRIVATE_B64"].strip()

    # Required runtime info
    agent = os.environ.get("AGENT_NAME", "").strip()
    if not agent:
        raise SystemExit("AGENT_NAME is required to mint a warrant.")

    module = os.environ.get("WARRANT_MODULE", "StegVerse-Labs/StegAgents").strip()
    bundle_sha256 = os.environ["TV_POLICY_BUNDLE_SHA256"].strip()

    host_platform = os.environ.get("HOST_PLATFORM", "github").strip()

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip() or os.environ.get("REPO", "").strip()
    commit_sha = os.environ.get("GITHUB_SHA", "").strip() or os.environ.get("COMMIT_SHA", "").strip()
    ref = os.environ.get("GITHUB_REF", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    workflow = os.environ.get("GITHUB_WORKFLOW", "").strip()
    actor = os.environ.get("GITHUB_ACTOR", "").strip()

    if not repo or not commit_sha:
        raise SystemExit("Missing repo/commit_sha (need GITHUB_REPOSITORY and GITHUB_SHA).")

    ttl_seconds = int(os.environ.get("WARRANT_TTL_SECONDS", "600").strip())
    issued_at = utc_now()
    expires_at = issued_at + timedelta(seconds=ttl_seconds)

    warrant = {
        "warrant_id": os.environ.get("WARRANT_ID", f"{int(issued_at.timestamp())}-{run_id or 'local'}-{agent}"),
        "issued_at": iso(issued_at),
        "expires_at": iso(expires_at),
        "issuer": issuer,
        "subject": {
            "type": "workflow_run" if host_platform == "github" else "execution",
            "id": f"{host_platform}:{repo}:{workflow}:{run_id}",
            "notes": "Ephemeral execution warrant"
        },
        "scope": {
            "action": "run_agent",
            "target": agent,
            "module": module,
            "permissions_intent": ["out:write"]
        },
        "policy": {
            "bundle_sha256": bundle_sha256
        },
        "claims": {
            "host_platform": host_platform,
            "repo": repo,
            "ref": ref,
            "commit_sha": commit_sha,
            "run_id": run_id,
            "workflow": workflow,
            "actor": actor
        }
    }

    payload = canonical_payload(warrant)

    priv = base64.b64decode(priv_b64)
    sk = SigningKey(priv)
    sig = sk.sign(payload).signature
    sig_b64 = base64.b64encode(sig).decode("utf-8")

    warrant["signature"] = {
        "alg": "ed25519",
        "public_key_id": public_key_id,
        "sig_b64": sig_b64
    }

    out = json.dumps(warrant, indent=2, sort_keys=True)
    print(out)

    # For CI: optionally emit hash line
    print(f"\n# warrant_payload_sha256={sha256_hex(payload)}")


if __name__ == "__main__":
    main()
