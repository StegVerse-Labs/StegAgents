# StegAgents

Central AI Entity runner for StegVerse-Labs.

This repo defines and runs multiple AI "entities" (agents) on schedules:

- `BookWriter-001` – long-form writing (books, memoirs, essays)
- `SocialMedia-001` – short-form posts for social channels
- `PatentAI-001` – patent-style research & draft content
- `GrantFinder-001` – scans for grant leads & summaries
- `DevOpsGuardian-001` – watches code health & suggests fixes

All agents:
- Are defined in `agents/registry.yml`
- Run via `.github/workflows/agents-cron.yml`
- Write Markdown outputs into `out/<agent_name>/YYYY-MM-DDTHHMMSSZ.md`

Set `OPENAI_API_KEY` as a **repo secret** to enable live runs.
