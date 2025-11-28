import os
import sys

from .agent_runner import run_agent

def main():
    # Agent name can come from env or CLI
    agent_name = os.environ.get("AGENT_NAME")
    if not agent_name and len(sys.argv) > 1:
        agent_name = sys.argv[1]

    if not agent_name:
        raise SystemExit("AGENT_NAME env var or CLI arg required")

    run_agent(agent_name)


if __name__ == "__main__":
    main()
