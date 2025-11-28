import os

from .agent_runner import run_agent


def main() -> None:
    agent_name = os.getenv("AGENT_NAME")
    if not agent_name:
        raise SystemExit(
            "AGENT_NAME environment variable is required but not set."
        )

    print(f"[StegAgents] main() starting with AGENT_NAME={agent_name!r}")
    run_agent(agent_name)
    print("[StegAgents] main() finished.")


if __name__ == "__main__":
    main()
