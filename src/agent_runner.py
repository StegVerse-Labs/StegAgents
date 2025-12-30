from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from stegcore import decide, ActionIntent  # StegCore policy decision
from .stegid_receipts import verify_receipt  # LOCAL verifier (vendored)

from .llm_client import call_llm
from .indexers import (
    harvester as idx_harvester,
    timeline as idx_timeline,
    multiverse as idx_multiverse,
    ethics as idx_ethics,
    gaps as idx_gaps,
    spine as idx_spine,
)

REPO_ROOT = Path(__file__).resolve().parents[1].parent
OUT_DIR = REPO_ROOT / "research" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------
# VerifiedReceipt loader (env injected by workflow)
# ---------------------------

def _load_receipt_from_env() -> Optional[dict]:
    raw = os.getenv("STEGID_VERIFIED_RECEIPT_JSON", "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _load_pubkeys() -> Dict[str, str]:
    """
    Where public keys are stored (kid -> public_b64url).
    Prefer local file in this repo at public_keys/keys.json.
    """
    p = REPO_ROOT / "public_keys" / "keys.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    raw = os.getenv("STEGID_PUBLIC_KEYS_JSON", "").strip()
    if raw:
        return json.loads(raw)
    return {}


def _as_stegcore_verified_receipt(receipt: dict) -> dict:
    return {
        "receipt_id": receipt.get("receipt_id", ""),
        "actor_class": receipt.get("actor_class", "ai"),
        "scopes": list(receipt.get("scopes", [])),
        "issued_at": receipt.get("issued_at", ""),
        "expires_at": receipt.get("expires_at", ""),
        "assurance_level": int(receipt.get("assurance_level", 0)),
        "signals": list(receipt.get("signals", [])),
        "proof": {
            "issuer": receipt.get("issuer", "stegid"),
            "kid": receipt.get("kid", ""),
            "payload_hash": receipt.get("payload_hash", ""),
            "sig": receipt.get("sig", ""),
        },
    }


class StegPermissionError(RuntimeError):
    pass


def _gate_agent_or_raise(agent_name: str) -> None:
    receipt = _load_receipt_from_env()
    if not receipt:
        raise StegPermissionError("DENY_NO_RECEIPT")

    pubkeys = _load_pubkeys()
    ok, reason = verify_receipt(receipt, pubkeys_by_kid=pubkeys)
    if not ok:
        raise StegPermissionError(f"DENY_BAD_RECEIPT:{reason}")

    verified = _as_stegcore_verified_receipt(receipt)

    intent = ActionIntent(
        action="agent_run",
        resource=f"agent:{agent_name}",
        scope="ai:run",
        parameters={"agent": agent_name},
    )

    decision = decide(verified, intent)
    if decision.verdict != "ALLOW":
        raise StegPermissionError(f"{decision.verdict}:{decision.reason_code}")


def _write_denial(agent_name: str, reason: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    out_path = OUT_DIR / f"{agent_name}__DENIED__{ts}.md"
    out_path.write_text(
        "\n".join(
            [
                f"# {agent_name} denied",
                "",
                f"- timestamp: {ts}",
                f"- reason: `{reason}`",
                "",
                "This agent did not run because StegID/StegCore did not authorize it.",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[{agent_name}] DENIED ({reason}) -> {out_path}")


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def _run_bookwriter() -> None:
    spine_path = OUT_DIR / "narrative_spine.md"
    spine = spine_path.read_text(encoding="utf-8") if spine_path.exists() else ""

    system_msg = (
        "You are the primary book architect for a long-form memoir + technical book. "
        "Using the narrative spine (which may be empty on the first run), propose a "
        "more detailed chapter-by-chapter outline. Do NOT write full prose chapters; "
        "focus on structure, beats, and what evidence or research each section relies on."
    )

    user_msg = (
        "Current narrative spine markdown (may be empty):\n\n"
        f"{spine}\n\n"
        "Produce an updated, more detailed outline in markdown."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=2600,
    )

    out_path = OUT_DIR / "book_outline.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[BookWriter-001] Wrote book outline to {out_path}")


def _run_social_media() -> None:
    spine_path = OUT_DIR / "narrative_spine.md"
    spine = spine_path.read_text(encoding="utf-8") if spine_path.exists() else ""

    system_msg = (
        "You are a careful social media strategist. Based on the narrative spine, "
        "write a small set of neutral, non-inflammatory posts that hint at the "
        "project themes (privacy, veterans, StrangeAuth, StegVerse) without "
        "revealing sensitive details or unverified allegations."
    )

    user_msg = (
        "Narrative spine (may be empty):\n\n"
        f"{spine}\n\n"
        "Produce:\n"
        "- 3 Facebook post drafts\n"
        "- 5 short-form posts (Twitter/Threads style)\n"
        "Return everything in markdown."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=1800,
    )

    out_path = OUT_DIR / "social_drafts.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[SocialMedia-001] Wrote social drafts to {out_path}")


def _run_grantfinder() -> None:
    gaps_path = OUT_DIR / "gap_analysis.json"
    gaps = gaps_path.read_text(encoding="utf-8") if gaps_path.exists() else ""

    system_msg = (
        "You are a grant strategy assistant focusing on early-stage, privacy, "
        "AI-safety, veterans, and civic-tech grants. Based on the gap analysis "
        "and implicit project themes, propose a list of concrete grant search "
        "vectors and project framings."
    )

    user_msg = (
        "Gap analysis JSON (may be empty):\n\n"
        f"{gaps}\n\n"
        "Produce a markdown file with:\n"
        "- Thematic areas\n"
        "- Proposed project titles and one-paragraph pitches\n"
        "- Keywords/phrases to search for in grant databases\n"
        "- Notes on timelines/urgency where appropriate."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=2000,
    )

    out_path = OUT_DIR / "grant_vectors.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[GrantFinder-001] Wrote grant vectors to {out_path}")


def _run_devops_guardian() -> None:
    gaps = (OUT_DIR / "gap_analysis.json").read_text(encoding="utf-8") if (
        OUT_DIR / "gap_analysis.json"
    ).exists() else ""
    deps_status = (OUT_DIR / "dependency_status.json").read_text(
        encoding="utf-8"
    ) if (OUT_DIR / "dependency_status.json").exists() else ""

    system_msg = (
        "You are a DevOps guardian for the StegVerse ecosystem. Given the gap "
        "analysis and any dependency status, propose an ordered list of concrete, "
        "bite-sized engineering tasks that can be automated or tackled next."
    )

    user_msg = (
        "Gap analysis JSON (may be empty):\n"
        f"{gaps}\n\n"
        "Dependency status JSON (may be empty):\n"
        f"{deps_status}\n\n"
        "Generate a markdown checklist of tasks with rough priority labels."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=1600,
    )

    out_path = OUT_DIR / "devops_tasklist.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[DevOpsGuardian-001] Wrote DevOps task list to {out_path}")


# Indexers
def _run_indexer_harvest() -> None:
    idx_harvester.run()


def _run_indexer_timeline() -> None:
    idx_timeline.run()


def _run_indexer_multiverse() -> None:
    idx_multiverse.run()


def _run_indexer_ethics() -> None:
    idx_ethics.run()


def _run_indexer_gaps() -> None:
    idx_gaps.run()


def _run_indexer_spine() -> None:
    idx_spine.run()


AGENTS: Dict[str, Callable[[], None]] = {
    "BookWriter-001": _run_bookwriter,
    "SocialMedia-001": _run_social_media,
    "GrantFinder-001": _run_grantfinder,
    "DevOpsGuardian-001": _run_devops_guardian,
    "Indexer-Harvest-001": _run_indexer_harvest,
    "Indexer-Timeline-001": _run_indexer_timeline,
    "Indexer-Multiverse-001": _run_indexer_multiverse,
    "Indexer-Ethics-001": _run_indexer_ethics,
    "Indexer-Gaps-001": _run_indexer_gaps,
    "Indexer-Spine-001": _run_indexer_spine,
}


def run_agent(agent_name: str) -> None:
    fn = AGENTS.get(agent_name)
    if not fn:
        raise SystemExit(f"Unknown agent: {agent_name!r}")

    try:
        _gate_agent_or_raise(agent_name)
    except StegPermissionError as e:
        _write_denial(agent_name, str(e))
        return

    fn()
