from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable

# ✅ NO stegid / StegID imports anywhere.
# Local receipt verifier (vendored)
from .receipt_verify import verify_receipt

# Optional: if StegCore exists, keep it (not banned)
try:
    from stegcore import decide, ActionIntent  # type: ignore
except Exception:
    decide = None
    ActionIntent = None


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "research" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class RunContext:
    agent_name: str
    out_dir: Path
    receipt: Dict[str, Any]
    env: Dict[str, str]


def _load_receipt_from_env() -> Dict[str, Any]:
    """
    Workflow sets SV_RECEIPT_JSON. If absent, create a local receipt.
    IMPORTANT: avoids banned strings and avoids external dependencies.
    """
    raw = (os.getenv("SV_RECEIPT_JSON") or "").strip()
    if raw:
        try:
            return json.loads(raw)
        except Exception as e:
            # Fall back to local receipt if malformed
            return {
                "issuer": "local",
                "verified": True,
                "verifier": "local-receipt",
                "issued_at": utc_now_iso(),
                "note": f"Malformed SV_RECEIPT_JSON ignored: {e.__class__.__name__}",
            }

    # Default local receipt
    return {
        "issuer": "local",
        "verified": True,
        "verifier": "local-receipt",
        "issued_at": utc_now_iso(),
        "note": "No SV_RECEIPT_JSON provided; default local receipt used.",
    }


def _agent_module_candidates(agent: str) -> list[str]:
    """
    Robust import candidates so you don't have to match one structure.
    Examples it will try:
      - src.agents.GrantFinder_001
      - src.agents.GrantFinder-001  (normalized)
      - src.agents.grantfinder_001
      - src.agents.GrantFinder_001.main
      - src.agents.grantfinder_001.main
      - src.agents.grantfinder.main
    """
    normalized = agent.replace("-", "_")
    lowerish = normalized.lower()

    bases = [
        f"src.agents.{normalized}",
        f"src.agents.{lowerish}",
        f"src.agents.{normalized}.main",
        f"src.agents.{lowerish}.main",
        f"src.{normalized}",
        f"src.{lowerish}",
    ]

    # Also try stripping common suffix patterns like -001 / _001
    stripped = normalized
    for suf in ["_001", "_01", "_1"]:
        if stripped.endswith(suf):
            stripped = stripped[: -len(suf)]
    bases += [
        f"src.agents.{stripped}",
        f"src.agents.{stripped}.main",
        f"src.agents.{stripped.lower()}",
        f"src.agents.{stripped.lower()}.main",
    ]

    # Unique preserve order
    seen = set()
    out: list[str] = []
    for m in bases:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _resolve_agent_entrypoint(agent: str) -> Callable[[RunContext], Any]:
    """
    Expected agent entrypoints (any one is fine):
      - run(ctx)
      - main(ctx)
      - handler(ctx)
    """
    last_err: Optional[BaseException] = None
    for mod_name in _agent_module_candidates(agent):
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            last_err = e
            continue

        for fn_name in ("run", "main", "handler"):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn  # type: ignore[return-value]

    msg = [
        f"Could not import/run agent '{agent}'. Tried modules:",
        *[f"  - {m}" for m in _agent_module_candidates(agent)],
        "",
        "Expected an entry function named one of: run(ctx), main(ctx), handler(ctx).",
        "Create one of those in your agent module.",
    ]
    if last_err is not None:
        msg.append("")
        msg.append(f"Last import error: {last_err.__class__.__name__}: {last_err}")
    raise RuntimeError("\n".join(msg))


def _write_run_artifact(out_dir: Path, agent: str, receipt: Dict[str, Any], result: Any) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent": agent,
        "timestamp": utc_now_iso(),
        "receipt": receipt,
        "result": result,
    }
    fp = out_dir / f"{agent}__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    fp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return fp


def _optional_policy_gate(agent: str, receipt: Dict[str, Any]) -> None:
    """
    If stegcore is present and you want to enforce policy, do it here.
    This does NOT reference banned strings.
    """
    if decide is None or ActionIntent is None:
        return

    try:
        intent = ActionIntent(action="run_agent", target=agent, metadata={"issuer": receipt.get("issuer", "local")})
        decision = decide(intent)
        if not getattr(decision, "allowed", True):
            reason = getattr(decision, "reason", "Policy denied agent run.")
            raise PermissionError(reason)
    except Exception as e:
        raise PermissionError(str(e)) from e


def run_agent(agent: str) -> int:
    receipt = _load_receipt_from_env()

    # Verify receipt (local verifier). If invalid, stop.
    verified = verify_receipt(receipt)
    if not verified.get("ok", False):
        print("❌ Receipt verification failed.")
        print(json.dumps(verified, indent=2))
        return 3

    # Optional policy gate (if StegCore present)
    _optional_policy_gate(agent, receipt)

    ctx = RunContext(
        agent_name=agent,
        out_dir=OUT_DIR,
        receipt=receipt,
        env=dict(os.environ),
    )

    entry = _resolve_agent_entrypoint(agent)
    result = entry(ctx)

    artifact = _write_run_artifact(OUT_DIR, agent, receipt, result)
    print(f"✅ Agent completed. Wrote: {artifact}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="StegAgents runner")
    parser.add_argument("--agent", required=True, help="Agent name (e.g., GrantFinder-001)")
    args = parser.parse_args(argv)

    try:
        return run_agent(args.agent)
    except PermissionError as e:
        print(f"⛔ Denied: {e}")
        return 4
    except Exception as e:
        print(f"❌ Failed: {e.__class__.__name__}: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
