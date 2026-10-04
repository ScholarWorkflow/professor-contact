#!/usr/bin/env python3
"""Build the fixed PC68-R1 request for the existing eval service."""
import argparse
import json
import shlex
from pathlib import Path


def build_request(consumer_root, prompt):
    consumer = str(Path(consumer_root).resolve())
    trust = 'projects={' + json.dumps(consumer) + '={trust_level="trusted"}}'
    argv = ["--json", "--skip-git-repo-check", "--sandbox", "workspace-write",
            "--cd", consumer, "--model", "gpt-5.6-luna",
            "--config", 'model_reasoning_effort="low"',
            "--config", "agents.max_concurrent_threads_per_session=2",
            "--config", trust, "--", prompt]
    return {"command": shlex.join(argv), "timeout": 900}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = build_request(args.consumer_root, args.prompt.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
