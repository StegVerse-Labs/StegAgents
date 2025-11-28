import os
import sys

from .agent_runner import run_agent


def main() -> None:
    """
    Entry point for all StegAgents and StegIndexers.

    AGENT_NAME is normally provided via environment in GitHub Actions
    (see agents-cron.yml and indexer-cron.yml), but we also accept a
    positional CLI argument for local runs:

        python -m src.main BookWriter-001
    """
    agent_name = os.environ.get("AGENT_NAME")

    if not agent_name and len(sys.argv) > 1:
        agent_name = sys.argv[1]

    if not agent_name:
        raise SystemExit(
            "AGENT_NAME not set and no agent name argument provided. "
            "Set AGENT_NAME env var or run: python -m src.main <AgentName>"
        )

    print(f"[StegAgents] Running agent: {agent_name}")
    run_agent(agent_name)


if __name__ == "__main__":
    main()
