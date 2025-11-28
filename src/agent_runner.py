from pathlib import Path
from typing import Callable, Dict

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

# ---------------------------------------------------------------------------
# High-level writer / utility agents
# ---------------------------------------------------------------------------


def _run_bookwriter() -> None:
    """
    BookWriter-001

    Uses the narrative spine (if present) to propose the next layer of
    detail for the book: chapter-level expansion notes.
    """
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
    """
    SocialMedia-001

    Drafts a small set of social posts capturing high-level themes without
    leaking sensitive details.
    """
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
    """
    GrantFinder-001

    Generates/updates a structured view of potential grant directions based
    on the current research gaps and project themes.
    """
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


def _run_patent_ai() -> None:
    """
    PatentAI-001

    Summarises potential patentable ideas based on the research gaps and
    narrative around StegVerse state engine / StrangeAuth.
    """
    gaps_path = OUT_DIR / "gap_analysis.json"
    gaps = gaps_path.read_text(encoding="utf-8") if gaps_path.exists() else ""

    system_msg = (
        "You are a patent strategy assistant. From the gap analysis and context, "
        "derive a list of potential patentable inventions related to:\n"
        "- StegVerse state engine / transient-code compute model\n"
        "- Ghost credential / phantom trust-break detection\n"
        "- Self-healing infrastructure guardians\n"
        "You are NOT writing patent claims; just categorised ideas and notes."
    )

    user_msg = (
        "Gap analysis JSON (may be empty):\n\n"
        f"{gaps}\n\n"
        "Produce markdown with sections:\n"
        "- Concept\n"
        "- Problem it solves\n"
        "- Rough novelty\n"
        "- Dependencies / prerequisites\n"
        "- Open questions."
    )

    content = call_llm(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=2000,
    )

    out_path = OUT_DIR / "patent_ideas.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[PatentAI-001] Wrote patent idea notes to {out_path}")


def _run_devops_guardian() -> None:
    """
    DevOpsGuardian-001

    Reads the various outputs and proposes concrete next-engineering steps
    for StegVerse/StegDB/StegAgents infrastructure.
    """
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


# ---------------------------------------------------------------------------
# Indexer agent mapping
# ---------------------------------------------------------------------------


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
    # Writer / utility agents
    "BookWriter-001": _run_bookwriter,
    "SocialMedia-001": _run_social_media,
    "GrantFinder-001": _run_grantfinder,
    "PatentAI-001": _run_patent_ai,
    "DevOpsGuardian-001": _run_devops_guardian,
    # Indexers
    "Indexer-Harvest-001": _run_indexer_harvest,
    "Indexer-Timeline-001": _run_indexer_timeline,
    "Indexer-Multiverse-001": _run_indexer_multiverse,
    "Indexer-Ethics-001": _run_indexer_ethics,
    "Indexer-Gaps-001": _run_indexer_gaps,
    "Indexer-Spine-001": _run_indexer_spine,
}


def run_agent(agent_name: str) -> None:
    """
    Dispatch entrypoint used by src.main.
    """
    fn = AGENTS.get(agent_name)
    if not fn:
        raise SystemExit(f"Unknown agent: {agent_name!r}")
    fn()
