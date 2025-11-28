import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from .models import AgentConfig
from .llm_client import call_llm

ROOT = Path(__file__).resolve().parent.parent

def load_registry() -> Dict[str, AgentConfig]:
    cfg_path = ROOT / "agents" / "registry.yml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    agents_raw = data.get("agents", [])

    registry: Dict[str, AgentConfig] = {}
    for item in agents_raw:
        cfg = AgentConfig(
            name=item["name"],
            enabled=bool(item.get("enabled", True)),
            model=item.get("model", "gpt-4.1"),
            system_prompt=item["system_prompt"],
            user_prompt=item["user_prompt"],
            output_dir=item["output_dir"],
        )
        registry[cfg.name] = cfg
    return registry


def run_agent(agent_name: str) -> Path:
    registry = load_registry()
    if agent_name not in registry:
        raise ValueError(f"Agent {agent_name!r} not found in registry.yml")

    cfg = registry[agent_name]
    if not cfg.enabled:
        raise RuntimeError(f"Agent {cfg.name} is disabled in registry.yml")

    print(f"[StegAgents] Running agent: {cfg.name}")

    content = call_llm(
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        user_prompt=cfg.user_prompt,
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = ROOT / cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}.md"

    header = f"# {cfg.name} output\n\nGenerated at (UTC): `{ts}`\n\n---\n\n"
    out_path.write_text(header + content, encoding="utf-8")

    print(f"[StegAgents] Wrote output: {out_path}")
    return out_path
