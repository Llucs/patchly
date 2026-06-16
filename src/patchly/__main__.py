from __future__ import annotations

import sys

from patchly.agent import Agent
from patchly.config import PatchlyConfig, load_config


def main():
    config = load_config()

    argv = sys.argv[1:]
    for arg in argv:
        if arg.startswith("--mode="):
            config.mode = arg.split("=", 1)[1]

    agent = Agent(config)
    exit_code = agent.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
