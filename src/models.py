# src/models.py
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


@dataclass(init=False)
class ActionIntent:
    """
    Flexible intent container.

    Key point: this class MUST accept `metadata=` because the runner passes it.
    Also: any extra kwargs are captured (and will not crash the workflow).
    """

    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.metadata = dict(metadata or {})

        # absorb any unexpected fields safely
        for k, v in kwargs.items():
            self.metadata[k] = v

        # optional convenience: expose keys as attributes too
        # (won't overwrite existing attrs like 'name'/'metadata')
        for k, v in self.metadata.items():
            if not hasattr(self, k):
                setattr(self, k, v)


__all__ = ["AgentConfig", "ActionIntent"]
