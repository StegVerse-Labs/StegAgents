import json
from datetime import datetime
from pathlib import Path

from ._paths import OUT_DIR
from ..llm_client import call_llm


FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"
TIMELINE_FILE = OUT_DIR / "timeline.json"


def run() -> None:
    """
    Indexer-Timeline-001

    Builds a coarse, human-readable timeline from harvested fragments.
    """
    if not FRAGMENTS_FILE.exists():
        print(
            "[Indexer-Timeline-001] No fragments found at "
            f"{FRAGMENTS_FILE}; run Indexer-Harvest-001 first."
        )
        return

    text = FRAGMENTS_FILE.read_text(encoding="utf-8")
    print(
        f"[Indexer-Timeline-001] Loaded {FRAGMENTS_FILE} "
        f"({len(text.splitlines())} fragments)."
    )

    system_msg = (
        "You are building a chronological timeline from JSONL research fragments. "
        "Each line is a JSON object as previously described. Produce a compact JSON "
        "structure of the form:\n"
        "{\n"
        '  "generated_at": iso8601,\n'
        '  "events": [\n'
        "     {\n"
        '       "id": str,\n'
        '       "approx_date_text": str,\n'
        '       "summary": str,\n'
        '       "actors": [str, ...],\n'
        '       "locations": [str, ...],\n'
        '       "source_ids": [str, ...],\n'
        '       "tags": [str, ...]\n'
        "     }, ...\n"
        "  ]\n"
        "}\n"
        "Sort events in chronological order based on the fragment dates when possible."
    )

    user_msg = (
        "Here are all research fragments as JSONL:\n\n"
        f"{text}\n\n"
        "Build the unified timeline JSON as described."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=2800,
    )

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        # Wrap raw LLM content into a minimal envelope
        obj = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "events": [],
            "raw": content,
        }

    TIMELINE_FILE.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Indexer-Timeline-001] Wrote timeline to {TIMELINE_FILE}")
