import json
from datetime import datetime
from pathlib import Path

from ._paths import OUT_DIR
from ..llm_client import call_llm


FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"
TIMELINE_FILE = OUT_DIR / "timeline.json"
GAPS_FILE = OUT_DIR / "gap_analysis.json"


def run() -> None:
    """
    Indexer-Gaps-001

    Analyses the corpus for missing pieces, contradictions, or areas that need
    more research before a book can be written.
    """
    fragments = (
        FRAGMENTS_FILE.read_text(encoding="utf-8")
        if FRAGMENTS_FILE.exists()
        else ""
    )
    timeline = (
        TIMELINE_FILE.read_text(encoding="utf-8")
        if TIMELINE_FILE.exists()
        else ""
    )

    system_msg = (
        "You are a research project planner. Given the fragments and timeline, "
        "identify open questions, missing evidence, and sections where further "
        "research is required. Output JSON:\n"
        "{\n"
        '  "generated_at": iso8601,\n'
        '  "open_questions": [str, ...],\n'
        '  "missing_evidence": [str, ...],\n'
        '  "priority_research_tasks": [str, ...],\n'
        '  "notes": str\n'
        "}"
    )

    user_msg = (
        "Timeline (may be empty):\n"
        f"{timeline}\n\n"
        "Fragments (JSONL, may be truncated):\n"
        f"{fragments[:5000]}\n\n"
        "Generate the gap analysis JSON."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=1800,
    )

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        obj = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "open_questions": [],
            "missing_evidence": [],
            "priority_research_tasks": [],
            "notes": content,
        }

    GAPS_FILE.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Indexer-Gaps-001] Wrote gap analysis to {GAPS_FILE}")
