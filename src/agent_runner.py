from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from .llm_client import call_llm


# === Agent definitions =====================================================

AGENT_PROMPTS: Dict[str, str] = {
    "BookWriter-001": (
        "You are BookWriter-001, a long-form writing assistant for StegVerse.\n"
        "Your job right now is to draft a focused, well-structured outline or "
        "short passage that can be used in a future book about StegVerse, "
        "automation, AI guardians, and Rigel's journey.\n\n"
        "Output must be in markdown.\n"
        "- Prefer concrete sections, headings, and bullet points.\n"
        "- Keep it self-contained and ready to drop into a manuscript."
    ),
    "SocialMedia-001": (
        "You are SocialMedia-001, a social media content generator for StegVerse.\n"
        "Create 3–5 punchy, positive posts that could be used on X (Twitter), "
        "Facebook, or LinkedIn.\n\n"
        "Each post should:\n"
        "- Be under 280 characters\n"
        "- Mention StegVerse or privacy/automation themes\n"
        "- Include 1–3 relevant hashtags.\n\n"
        "Output as a numbered markdown list."
    ),
    "GrantFinder-001": (
        "You are GrantFinder-001, a grant and funding opportunity scout.\n"
        "Summarize the types of grants, accelerators, or early-stage funding "
        "StegVerse should target over the next 30 days.\n\n"
        "Focus on:\n"
        "- AI, privacy, cybersecurity, digital rights\n"
        "- US-based opportunities around $25k–$150k\n"
        "- Any specific programs or foundations StegVerse should investigate.\n\n"
        "Output as markdown with headings and bullet points.\n"
        "You may not browse the internet; instead, reason from general knowledge "
        "about typical grant landscapes."
    ),
    "DevOpsGuardian-001": (
        "You are DevOpsGuardian-001, the DevOps and reliability strategist for "
        "StegVerse.\n"
        "Produce a concise status memo suggesting:\n"
        "- Next steps for making StegVerse repos more self-healing\n"
        "- Ideas for additional GitHub Actions guardians or monitors\n"
        "- Any risks you foresee in CI/CD or secrets management.\n\n"
        "Output in markdown with clear sections and actionable bullet points."
    ),
}


# === Agent runner ==========================================================


def build_prompt(agent_name: str) -> str:
    """Build the final prompt sent to the LLM for a given agent."""
    base = AGENT_PROMPTS.get(agent_name)
    if not base:
        raise ValueError(f"Unknown agent name: {agent_name}")

    now = datetime.now(timezone.utc).isoformat()
    return (
        f"{base}\n\n"
        f"Timestamp (UTC): {now}\n"
        f"Make sure your output stands on its own without needing this context."
    )


def run_agent(agent_name: str) -> None:
    """
    Run a single StegAgent by name.

    This function is intentionally defensive:
    - It catches and logs all exceptions so the GitHub Action job does not hard-fail.
    - It prints the agent output to stdout for now (later we can commit files
      or open issues/PRs).
    """
    print(f"[StegAgents] Starting agent: {agent_name}")

    try:
        prompt = build_prompt(agent_name)
    except Exception as exc:
        print(f"[StegAgents] ERROR building prompt for {agent_name}: {exc}")
        # Do not re-raise; keep the workflow green.
        return

    try:
        content = call_llm(prompt)
    except Exception as exc:
        print(f"[StegAgents] ERROR during LLM call for {agent_name}: {exc}")
        # We deliberately do NOT re-raise here. This keeps the job from failing
        # even under bad network / rate-limit situations after all retries.
        return

    print(f"[StegAgents] Agent {agent_name} completed successfully.\n")
    print("===== AGENT OUTPUT BEGIN =====")
    print(content)
    print("===== AGENT OUTPUT END =====")
