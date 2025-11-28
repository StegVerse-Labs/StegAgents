from dataclasses import dataclass

@dataclass
class AgentConfig:
    name: str
    enabled: bool
    model: str
    system_prompt: str
    user_prompt: str
    output_dir: str
