from __future__ import annotations

import sys
import argparse

from patchly.agent import Agent
from patchly.config import PatchlyConfig, load_config


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description='Patchly agent')
    parser.add_argument('--mode', choices=['review', 'scan', 'fix', 'continuous', 'command'],
                        help='Operating mode')
    args, unknown = parser.parse_known_args()

    if args.mode:
        config.mode = args.mode

    agent = Agent(config)
    exit_code = agent.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()