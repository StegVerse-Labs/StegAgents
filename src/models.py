from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AgentConfig:
    name: str
    enabled: bool
    model: str
    system_prompt: str
    user_prompt: str
    output_dir: str


@dataclass
class ActionIntent:
    """
    A lightweight intent envelope for agent actions.

    `metadata` is optional and defaults to {} so callers can safely pass
    extra context without breaking older constructors.
    """
    agent: str
    action: str
    message: str = ""
    output_dir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
