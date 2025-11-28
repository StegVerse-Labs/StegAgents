"""
Indexer-FreeDom-001
--------------------

Bridges structured/semi-structured data from the FREE-DOM repository
into StegAgents' unified research fragment format.

This file **creates** research_fragments.jsonl entries from:

- data/master/        (high confidence, canonical)
- data/unverified/    (low confidence leads)
- data/summary/       (aggregated dashboards)
- data/logs/ai_agent/ (public-source news hits)

Fragments written here are consumed by:
- spine.py (Indexer-Spine-001)
- timeline.py
- Writer agents
- Social AI agents
- GrantFinder-001
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict

from ._paths import OUT_DIR, STATE_DIR
from ..llm_client import call_llm


# -------------------------------------------------------
# Where the FREE-DOM repo is located (checked out by workflow)
# -------------------------------------------------------
FREE_DOM_ROOT = Path(__file__).resolve().parents[2] / "FREE-DOM"

# -------------------------------------------------------
# State tracking
# -------------------------------------------------------
STATE_FILE = STATE_DIR / "freedom_processed_files.txt"
FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"

# -------------------------------------------------------
# Buckets: knows confidence + evidence type for each data zone
# -------------------------------------------------------
BUCKETS: List[Dict[str, object]] = [
    {
        "name": "master",
        "path": FREE_DOM_ROOT / "data" / "master",
        "default_evidence_type": "public_record",
        "default_confidence": "high",
    },
    {
        "name": "unverified",
        "path": FREE_DOM_ROOT / "data" / "unverified",
        "default_evidence_type": "unverified",
        "default_confidence": "low",
    },
    {
        "name": "summary",
        "path": FREE_DOM_ROOT / "data" / "summary",
        "default_evidence_type": "summary",
        "default_confidence": "medium",
    },
    {
        "name": "logs",
        "path": FREE_DOM_ROOT / "data" / "logs" / "ai_agent",
        "default_evidence_type": "news",
        "default_confidence": "medium",
    },
]


# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------
def _load_processed() -> set:
    if not STATE_FILE.exists():
        return set()
    return {
        line.strip()
        for line in STATE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _save_processed(keys: List[str]) -> None:
    existing = _load_processed()
    existing.update(keys)
    STATE_FILE.write_text("\n".join(sorted(existing)) + "\n", encoding="utf-8")


def _iter_new_files() -> List[Tuple[Path, str, Dict[str, object]]]:
    """
    Return a list of (path, rel_id, bucket_cfg) for each NEW file under FREE-DOM.
    """
    processed = _load_processed()
    results = []

    if not FREE_DOM_ROOT.exists():
        print(f"[Indexer-FreeDom-001] FREE-DOM repo missing at {FREE_DOM_ROOT}")
        return results

    for bucket in BUCKETS:
        base = bucket["path"]
        bucket_name = bucket["name"]

        if not base.exists():
            continue

        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue

            rel_id = path.relative_to(FREE_DOM_ROOT).as_posix()
            key = f"{bucket_name}::{rel_id}"

            if key in processed:
                continue

            # skip binary / images
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip"}:
                continue

            results.append((path, rel_id, bucket))

    return results


# -------------------------------------------------------
# Main runner
# -------------------------------------------------------
def run() -> None:
    """
    Main entry for the FREE-DOM data indexer.

    Produces uniform research fragments from heterogeneous FREE-DOM datasets.
    """
    new_files = _iter_new_files()
    if not new_files:
        print("[Indexer-FreeDom-001] No new files to process.")
        return

    print(f"[Indexer-FreeDom-001] Processing {len(new_files)} new FREE-DOM file(s).")

    processed_keys = []

    with FRAGMENTS_FILE.open("a", encoding="utf-8") as fh:
        for path, rel_id, bucket in new_files:
            bucket_name = bucket["name"]
            default_evidence_type = bucket["default_evidence_type"]
            default_confidence = bucket["default_confidence"]

            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                print(f"[Indexer-FreeDom-001] Failed to read {rel_id}: {exc}")
                continue

            print(
                f"[Indexer-FreeDom-001] → Indexing {rel_id}"
                f" — bucket={bucket_name}, size={len(raw)} chars"
            )

            # -------------------------------------------------------
            # LLM instructions
            # -------------------------------------------------------
            system_msg = (
                "You are a research indexer converting factual data into structured "
                "research fragments. Use ONLY the content provided. DO NOT invent.\n\n"
                "Bucket semantics:\n"
                "- master: verified high-confidence public record\n"
                "- unverified: leads, unconfirmed, low confidence\n"
                "- summary: aggregate dashboards and coverage maps\n"
                "- logs: raw RSS/news scan hits\n\n"
                "Return only newline-separated JSON objects with schema:\n"
                "{\n"
                '  "source_repo": "FREE-DOM",\n'
                '  "source_bucket": "...",\n'
                '  "source_id": str,\n'
                '  "source_path": str,\n'
                '  "approx_date_text": str,\n'
                '  "summary": str,\n'
                '  "key_points": [str],\n'
                '  "actors": [str],\n'
                '  "locations": [str],\n'
                '  "tags": [str],\n'
                '  "evidence_type": "...",\n'
                '  "confidence": "high|medium|low"\n'
                "}\n"
            )

            user_msg = (
                f"FREE-DOM file: {rel_id}\n"
                f"Bucket: {bucket_name}\n"
                f"Ingested: {datetime.utcnow().isoformat()}Z\n\n"
                f"Content:\n{raw}"
            )

            response = call_llm(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=1500,
            )

            # -------------------------------------------------------
            # Parse each JSONL line
            # -------------------------------------------------------
            for line in response.splitlines():
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    obj = {
                        "source_repo": "FREE-DOM",
                        "source_bucket": bucket_name,
                        "source_id": f"fallback::{rel_id}",
                        "source_path": rel_id,
                        "approx_date_text": "",
                        "summary": line,
                        "key_points": [],
                        "actors": [],
                        "locations": [],
                        "tags": ["fallback"],
                        "evidence_type": default_evidence_type,
                        "confidence": default_confidence,
                    }

                # Ensure defaults exist
                obj.setdefault("source_repo", "FREE-DOM")
                obj.setdefault("source_bucket", bucket_name)
                obj.setdefault("source_path", rel_id)
                obj.setdefault("evidence_type", default_evidence_type)
                obj.setdefault("confidence", default_confidence)

                fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

            processed_keys.append(f"{bucket_name}::{rel_id}")

    _save_processed(processed_keys)
    print("[Indexer-FreeDom-001] Completed & state updated.")
