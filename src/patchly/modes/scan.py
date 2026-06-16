from __future__ import annotations

from patchly.config import PatchlyConfig
from patchly.agent import Agent


def execute(config: PatchlyConfig) -> int:
    config.mode = "scan"
    agent = Agent(config)
    return agent.run()
