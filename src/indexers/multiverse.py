import json
from pathlib import Path

from ._paths import OUT_DIR
from ..llm_client import call_llm


TIMELINE_FILE = OUT_DIR / "timeline.json"
FRAGMENTS_FILE = OUT_DIR / "research_fragments.jsonl"
PLOTS_FILE = OUT_DIR / "plot_branches.json"


def run() -> None:
    """
    Indexer-Multiverse-001

    Given the timeline + fragments, propose alternate narrative branches:
    different ways to tell the story while staying anchored to facts.
    """
    if not TIMELINE_FILE.exists():
        print(
            "[Indexer-Multiverse-001] No timeline.json; run Indexer-Timeline-001 first."
        )
        return

    timeline = TIMELINE_FILE.read_text(encoding="utf-8")
    fragments = (
        FRAGMENTS_FILE.read_text(encoding="utf-8")
        if FRAGMENTS_FILE.exists()
        else ""
    )

    system_msg = (
        "You are a narrative architect. Given a factual timeline and research "
        "fragments, enumerate several plausible narrative 'branches' (ways to "
        "tell the story) that remain honest to the underlying evidence.\n\n"
        "Output JSON:\n"
        "{\n"
        '  "branches": [\n'
        "    {\n"
        '      "id": str,\n'
        '      "label": str,\n'
        '      "description": str,\n'
        '      "emphasis": ["technical", "personal", "political", "spiritual", ...],\n'
        '      "key_events": [event_id, ...]\n'
        "    }, ...\n"
        "  ]\n"
        "}"
    )

    user_msg = (
        "Timeline JSON:\n"
        f"{timeline}\n\n"
        "Research fragments (JSONL, may be truncated):\n"
        f"{fragments[:4000]}\n\n"
        "Build the branches JSON."
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
        obj = {"branches": [], "raw": content}

    PLOTS_FILE.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Indexer-Multiverse-001] Wrote plot branches to {PLOTS_FILE}")
