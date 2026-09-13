#!/usr/bin/env python3
"""Configure the OpenCode subagent depth budget for a professor-contact install.

Part of the official OpenCode install contract (run after ``apm install``):
writes ``subagent_depth >= 3`` into the consumer project's ``opencode.json``.
APM deploys only agent/skill primitives and cannot carry project config, so
this step is producer-owned, deterministic and idempotent; it never downgrades
an already-higher depth and never overwrites a corrupt config.

Exit codes: 0 ok, 2 needs_config/usage, 3 ambiguous config, 4 invalid config.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REQUIRED_DEPTH = 3
SCHEMA = "https://opencode.ai/config.json"


def _config_candidates(project_root: Path):
    return (
        project_root / "opencode.json",
        project_root / ".opencode" / "opencode.json",
    )


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(
            f"configure_opencode_depth: {path}: invalid JSON ({exc}); "
            "refusing to overwrite a corrupt config",
            file=sys.stderr,
        )
        raise SystemExit(4)


def _resolve_target(project_root: Path):
    root_config, dotdir_config = _config_candidates(project_root)
    if root_config.is_file():
        return root_config
    if dotdir_config.is_file():
        return dotdir_config
    return root_config


def _emit(payload):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Write subagent_depth >= 3 into the project opencode.json "
            "(professor-contact official OpenCode install step)."
        )
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="consumer project root (default: current directory)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=REQUIRED_DEPTH,
        help="minimum depth budget to enforce (default: 3)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify only; never write",
    )
    args = parser.parse_args(argv)
    if args.depth < 1:
        parser.error("--depth must be >= 1")

    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        parser.error(f"project root does not exist: {project_root}")

    root_config, dotdir_config = _config_candidates(project_root)
    target = _resolve_target(project_root)

    root_data = _load_json(root_config)
    dotdir_data = _load_json(dotdir_config) if dotdir_config.is_file() else None

    if (
        root_data is not None
        and dotdir_data is not None
        and isinstance(dotdir_data, dict)
        and isinstance(dotdir_data.get("subagent_depth"), int)
        and dotdir_data["subagent_depth"] < args.depth
        and target == root_config
    ):
        _emit(
            {
                "status": "ambiguous",
                "reason": "dotdir opencode.json defines a smaller depth; "
                "OpenCode precedence between root and .opencode configs is "
                "not guaranteed here",
                "root": str(root_config),
                "dotdir": str(dotdir_config),
            }
        )
        return 3

    if not isinstance(target, Path):
        parser.error("unreachable config target resolution")

    data = _load_json(target)
    if data is None:
        current = None
    elif not isinstance(data, dict):
        print(
            f"configure_opencode_depth: {target}: config root is not a JSON object",
            file=sys.stderr,
        )
        return 4
    else:
        current = data.get("subagent_depth")
        if current is not None and not isinstance(current, int):
            print(
                f"configure_opencode_depth: {target}: subagent_depth is not an integer",
                file=sys.stderr,
            )
            return 4

    effective = current if current is not None else None
    if effective is not None and effective >= args.depth:
        _emit(
            {
                "status": "ok",
                "effective_depth": effective,
                "path": str(target),
                "action": "none",
            }
        )
        return 0

    if args.check:
        _emit(
            {
                "status": "needs_config",
                "effective_depth": effective,
                "path": str(target),
                "action": "would_write",
            }
        )
        return 2

    new_depth = max(current or 0, args.depth)
    if data is None:
        data = {"$schema": SCHEMA, "subagent_depth": new_depth}
    else:
        data["subagent_depth"] = new_depth

    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=".opencode.json.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    _emit(
        {
            "status": "ok",
            "effective_depth": new_depth,
            "path": str(target),
            "action": "wrote",
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
