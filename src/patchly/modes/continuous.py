from __future__ import annotations

from patchly.config import PatchlyConfig


def execute(config: PatchlyConfig) -> int:
    from patchly.agent import Agent

    agent = Agent(config)
    return agent.run()
