import argparse
import importlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from .models import ActionIntent
from .warrant_verify import verify_warrant

OUT_DIR = Path("out")
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RunContext:
    agent_name: str
    receipt: Dict[str, Any]  # kept name for compatibility; now holds the warrant
    metadata: Dict[str, Any]


def _agent_module_candidates(agent: str) -> list[str]:
    normalized = agent.replace("-", "_")
    lowerish = normalized.lower()

    stripped = normalized
    while stripped and stripped[0].isdigit():
        stripped = stripped[1:]
    stripped = stripped.strip("_") or normalized

    return [
        f"src.agents.{normalized}",
        f"src.agents.{lowerish}",
        f"src.agents.{normalized}.main",
        f"src.agents.{lowerish}.main",
        f"src.agents.{stripped}",
        f"src.agents.{stripped}.main",
        f"src.agents.{stripped.lower()}",
        f"src.agents.{stripped.lower()}.main",
    ]


def _resolve_agent_entrypoint(agent: str) -> Callable[[RunContext], Any]:
    last_err = None
    for mod_name in _agent_module_candidates(agent):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "run") and callable(getattr(mod, "run")):
                return getattr(mod, "run")
            if hasattr(mod, "main") and callable(getattr(mod, "main")):
                return getattr(mod, "main")
        except Exception as e:
            last_err = e

    tried = "\n".join([f"  - {m}" for m in _agent_module_candidates(agent)])
    raise RuntimeError(
        f"Could not import/run agent '{agent}'. Tried modules:\n{tried}\n"
        f"Last error: {last_err}\n"
        "Create a module with a `run(ctx)` or `main(ctx)` entrypoint."
    )


def _write_run_artifact(out_dir: Path, agent: str, warrant: Dict[str, Any], result: Any) -> Path:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agent": agent,
        "warrant_id": warrant.get("warrant_id"),
        "issuer": warrant.get("issuer"),
        "policy_bundle_sha256": (warrant.get("policy") or {}).get("bundle_sha256"),
        "claims": warrant.get("claims", {}),
        "result": result,
    }
    fp = out_dir / f"{agent}__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    fp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return fp


def _load_warrant_from_env() -> Dict[str, Any]:
    raw = os.getenv("STEGVERSE_WARRANT_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing STEGVERSE_WARRANT_JSON (Execution Warrant required).")
    try:
        return json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Invalid STEGVERSE_WARRANT_JSON: {e}")


def _load_tv_public_key_b64() -> str:
    # For Sprint 1: simplest path is to pass issuer pubkey via env in CI.
    # Sprint 2: load from TV-exported bundle pinned by hash.
    pk = os.getenv("TV_WARRANT_ISSUER_PUBKEY_B64", "").strip()
    if not pk:
        raise RuntimeError("Missing TV_WARRANT_ISSUER_PUBKEY_B64.")
    return pk


def _required_policy_gate(agent: str, warrant: Dict[str, Any]) -> None:
    # Optional StegCore gate hook preserved, but warrant validation is always required.
    # If you have StegCore installed, you can enforce additional policy here.
    try:
        from .stegcore_guard import enforce_policy  # type: ignore

        intent = ActionIntent(action="run_agent", target=agent, metadata={"issuer": warrant.get("issuer", "unknown")})
        decision = enforce_policy(intent=intent, receipt=warrant)
        verdict = getattr(decision, "verdict", "ALLOW")
        if verdict != "ALLOW":
            reason = getattr(decision, "reason", "Policy denied agent run.")
            raise RuntimeError(f"DENIED_BY_STEGCORE: {verdict} {reason}")
    except ModuleNotFoundError:
        # No StegCore in repo: that's fine for Sprint 1.
        return


def run_agent(agent: str) -> int:
    mode = os.getenv("STEGVERSE_POLICY_MODE", "strict").strip().lower()
    if mode not in ("strict", "warn", "off"):
        mode = "strict"

    warrant = _load_warrant_from_env()

    expected_bundle = os.getenv("TV_POLICY_BUNDLE_SHA256", "").strip()
    if not expected_bundle:
        raise RuntimeError("Missing TV_POLICY_BUNDLE_SHA256 (pinning required).")

    repo = os.getenv("GITHUB_REPOSITORY", "").strip() or os.getenv("REPO", "").strip()
    commit_sha = os.getenv("GITHUB_SHA", "").strip() or os.getenv("COMMIT_SHA", "").strip()
    if not repo or not commit_sha:
        raise RuntimeError("Missing observed repo/commit (need GITHUB_REPOSITORY and GITHUB_SHA).")

    issuer_pubkey_b64 = _load_tv_public_key_b64()
    max_ttl = int(os.getenv("TV_WARRANT_MAX_TTL_SECONDS", "900").strip())

    decision = verify_warrant(
        warrant=warrant,
        issuer_pubkey_b64=issuer_pubkey_b64,
        expected_bundle_sha256=expected_bundle,
        observed_repo=repo,
        observed_commit_sha=commit_sha,
        max_ttl_seconds=max_ttl,
    )

    if not decision.ok:
        msg = f"❌ Warrant verification failed: {decision.reason}"
        if mode == "warn":
            print(msg)
        elif mode == "off":
            print("⚠️ Policy mode off; ignoring warrant failure.")
        else:
            raise RuntimeError(msg)
    else:
        print(f"✅ Warrant verified. payload_sha256={decision.payload_sha256}")

    # Additional policy gate (if StegCore present)
    if mode != "off":
        _required_policy_gate(agent, warrant)

    ctx = RunContext(agent_name=agent, receipt=warrant, metadata={})
    entry = _resolve_agent_entrypoint(agent)
    result = entry(ctx)

    artifact = _write_run_artifact(OUT_DIR, agent, warrant, result)
    print(f"✅ Agent completed. Wrote: {artifact}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="StegAgents runner")
    parser.add_argument("--agent", required=True, help="Agent name (e.g., GrantFinder-001)")
    args = parser.parse_args()
    return run_agent(args.agent)


if __name__ == "__main__":
    raise SystemExit(main())
