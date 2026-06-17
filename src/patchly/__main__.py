from __future__ import annotations

import sys

from patchly.agent import Agent
from patchly.config import PatchlyConfig, load_config

VALID_MODES = {"auto", "fix", "review", "scan", "command", "continuous"}


def main():
    config = load_config()

    argv = sys.argv[1:]
    for arg in argv:
        if arg.startswith("--mode="):
            mode_value = arg.split("=", 1)[1]
            if mode_value not in VALID_MODES:
                print(f"Error: Invalid mode '{mode_value}'. Allowed modes: {', '.join(VALID_MODES)}", file=sys.stderr)
                sys.exit(1)
            config.mode = mode_value

    agent = Agent(config)
    exit_code = agent.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()