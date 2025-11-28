import json
from datetime import datetime
from pathlib import Path
from typing import List

from ._paths import INBOX_DIR, OUT_DIR, STATE_DIR
from ..llm_client import call_llm


STATE_FILE = STATE_DIR / "harvested_files.txt"
FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"


def _load_processed() -> set:
    if not STATE_FILE.exists():
        return set()
    return set(x.strip() for x in STATE_FILE.read_text().splitlines() if x.strip())


def _save_processed(files: List[str]) -> None:
    existing = _load_processed()
    existing.update(files)
    STATE_FILE.write_text("\n".join(sorted(existing)) + "\n")


def _iter_new_files():
    processed = _load_processed()
    for path in sorted(INBOX_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(INBOX_DIR).as_posix()
        if rel in processed:
            continue
        yield path, rel


def run() -> None:
    """
    Indexer-Harvest-001

    Reads raw text/markdown files from research/inbox and converts them
    into structured JSONL fragments in research/out/research_fragments.jsonl
    using the LLM as a semantic indexer.
    """
    new_files = list(_iter_new_files())
    if not new_files:
        print("[Indexer-Harvest-001] No new files in research/inbox.")
        return

    print(f"[Indexer-Harvest-001] Processing {len(new_files)} new file(s).")

    fragments_fh = FRAGMENTS_FILE.open("a", encoding="utf-8")
    processed_names = []

    for path, rel in new_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        print(f"[Indexer-Harvest-001] Indexing {rel} ({len(text)} chars)")

        system_msg = (
            "You are a research indexer for a long-form investigative memoir and "
            "technical book. Extract a set of JSON fragments capturing key events, "
            "claims, evidence, actors, dates, locations and tags from the source "
            "text. Each fragment is one JSON object on its own line. The schema:\n"
            "{\n"
            '  "source_id": str,\n'
            '  "source_path": str,\n'
            '  "approx_date_text": str,\n'
            '  "summary": str,\n'
            '  "key_points": [str, ...],\n'
            '  "actors": [str, ...],\n'
            '  "locations": [str, ...],\n'
            '  "tags": [str, ...],\n'
            '  "evidence_type": "personal_observation|public_record|news|speculation|other",\n'
            '  "confidence": "low|medium|high"\n'
            "}\n"
            "Return ONLY newline-separated JSON objects. No commentary."
        )

        user_msg = (
            f"Source path: {rel}\n"
            f"Ingested at: {datetime.utcnow().isoformat()}Z\n\n"
            "Full text:\n"
            f"{text}"
        )

        content = call_llm(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=1400,
        )

        # Split by lines and keep the ones that look like JSON
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Wrap raw text into a generic fragment
                obj = {
                    "source_id": f"fallback::{rel}",
                    "source_path": rel,
                    "approx_date_text": "",
                    "summary": line,
                    "key_points": [],
                    "actors": [],
                    "locations": [],
                    "tags": ["fallback-parse"],
                    "evidence_type": "other",
                    "confidence": "low",
                }
            fragments_fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

        processed_names.append(rel)

    fragments_fh.close()
    _save_processed(processed_names)
    print(
        f"[Indexer-Harvest-001] Wrote fragments to {FRAGMENTS_FILE} "
        f"and updated {STATE_FILE}"
    )
