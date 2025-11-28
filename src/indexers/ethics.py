import json
from datetime import datetime
from pathlib import Path

from ._paths import OUT_DIR
from ..llm_client import call_llm


FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"
TIMELINE_FILE = OUT_DIR / "timeline.json"
ETHICS_FILE = OUT_DIR / "ethics_report.json"


def run() -> None:
    """
    Indexer-Ethics-001

    Reviews the research corpus and timeline for ethical / safety concerns and
    produces a structured ethics guidance JSON.
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
        "You are an ethics / safety reviewer for a memoir+technical book. "
        "Identify: (1) sensitive topics, (2) legal risk, (3) privacy concerns, "
        "(4) where strong disclaimers are required, and (5) red lines that "
        "should not be crossed. Output JSON with:\n"
        "{\n"
        '  "generated_at": iso8601,\n'
        '  "sensitive_topics": [str, ...],\n'
        '  "required_disclaimers": [str, ...],\n'
        '  "privacy_risks": [str, ...],\n'
        '  "legal_risks": [str, ...],\n'
        '  "red_lines": [str, ...],\n'
        '  "notes": str\n'
        "}"
    )

    user_msg = (
        "Timeline (may be empty):\n"
        f"{timeline}\n\n"
        "Fragments (JSONL, may be truncated):\n"
        f"{fragments[:5000]}\n\n"
        "Generate the ethics JSON as described."
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
            "sensitive_topics": [],
            "required_disclaimers": [],
            "privacy_risks": [],
            "legal_risks": [],
            "red_lines": [],
            "notes": content,
        }

    ETHICS_FILE.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Indexer-Ethics-001] Wrote ethics report to {ETHICS_FILE}")
