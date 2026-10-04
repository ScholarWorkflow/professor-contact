#!/usr/bin/env python3
"""Observe shared Codex eval-service storage isolation without running a model.

The existing eval service is allowed to persist Codex state only when it uses a
test-only CODEX_HOME and test-only SQLite/log locations. This helper inspects
the already-running service process and its CODEX_HOME/config.toml; it does not
start, stop, restart, or send an /eval request.
"""
import argparse
import json
import subprocess
import tomllib
from pathlib import Path

import run_issue68_stage5_routing_r14_codex as formal


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def process_environment_text(pid):
    return subprocess.check_output(["ps", "eww", "-p", str(pid), "-o", "command="], text=True)


def environment_value(text, name):
    marker = f" {name}="
    index = text.find(marker)
    if index < 0:
        if text.startswith(f"{name}="):
            start = len(name) + 1
        else:
            return None
    else:
        start = index + len(marker)
    value = text[start:].split(" ", 1)[0].strip()
    return value or None


def resolve_under_home(value, codex_home):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = codex_home / path
    return path.resolve()


def is_within(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path == root or path.is_relative_to(root)


def capture_storage_isolation(service):
    pid = service["pid"]
    env_text = process_environment_text(pid)
    codex_home_raw = environment_value(env_text, "CODEX_HOME")
    sqlite_env_raw = environment_value(env_text, "CODEX_SQLITE_HOME")
    if not codex_home_raw:
        raise ValueError("eval_service_codex_home_missing")
    if any(char.isspace() for char in codex_home_raw):
        raise ValueError("eval_service_codex_home_unparseable")

    codex_home = Path(codex_home_raw).expanduser().resolve()
    if codex_home == (Path.home() / ".codex").resolve():
        raise ValueError("eval_service_uses_production_codex_home")
    if not codex_home.is_dir():
        raise ValueError("eval_service_codex_home_missing_on_disk")

    config_path = codex_home / "config.toml"
    config = {}
    if config_path.is_file():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("eval_service_config_malformed")

    sqlite_config_raw = config.get("sqlite_home")
    log_config_raw = config.get("log_dir")
    if sqlite_config_raw is not None and not isinstance(sqlite_config_raw, str):
        raise ValueError("eval_service_sqlite_home_malformed")
    if log_config_raw is not None and not isinstance(log_config_raw, str):
        raise ValueError("eval_service_log_dir_malformed")

    sqlite_config = resolve_under_home(sqlite_config_raw, codex_home) if sqlite_config_raw else None
    sqlite_env = resolve_under_home(sqlite_env_raw, codex_home) if sqlite_env_raw else None
    log_config = resolve_under_home(log_config_raw, codex_home) if log_config_raw else None

    for path, reason in (
        (sqlite_config, "eval_service_sqlite_home_not_test_only"),
        (sqlite_env, "eval_service_sqlite_env_not_test_only"),
        (log_config, "eval_service_log_dir_not_test_only"),
    ):
        if path is not None and not is_within(path, codex_home):
            raise ValueError(reason)

    sqlite_effective = sqlite_config or sqlite_env or codex_home
    sqlite_source = "config.sqlite_home" if sqlite_config else ("CODEX_SQLITE_HOME" if sqlite_env else "CODEX_HOME fallback")
    log_effective = log_config
    log_source = "config.log_dir" if log_config else "CODEX_HOME-derived default"

    return {
        "status": "ISOLATION_CONFIRMED",
        "service_pid": pid,
        "service_cwd": service["cwd"],
        "codex_home": str(codex_home),
        "production_default_codex_home": str((Path.home() / ".codex").resolve()),
        "config_path": str(config_path),
        "config_present": config_path.is_file(),
        "sqlite": {
            "config_sqlite_home": str(sqlite_config) if sqlite_config else None,
            "inherited_CODEX_SQLITE_HOME": str(sqlite_env) if sqlite_env else None,
            "effective_path": str(sqlite_effective),
            "source": sqlite_source,
            "inside_test_codex_home": is_within(sqlite_effective, codex_home),
        },
        "log": {
            "config_log_dir": str(log_config) if log_config else None,
            "effective_path": str(log_effective) if log_effective else None,
            "source": log_source,
            "inside_test_codex_home": True if log_effective is None else is_within(log_effective, codex_home),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-direnv-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        print(json.dumps({"status": "CASE_NOT_STARTED", "reason_code": "output_directory_not_empty"}))
        return 2
    output.mkdir(parents=True, exist_ok=True)

    try:
        contract = formal.load_contract()
        eval_root = args.eval_direnv_root.resolve()
        revision = formal.base.clean_revision(eval_root, contract["eval_server_revision"])
        port = formal.resolve_eval_port(eval_root)
        service = formal.capture_service_instance(eval_root, port)
        isolation = capture_storage_isolation(service)
        result = {
            "status": "ISOLATION_CONFIRMED",
            "eval_server": revision,
            "service": service,
            "storage": isolation,
        }
    except (OSError, ValueError, subprocess.SubprocessError, tomllib.TOMLDecodeError) as exc:
        result = {
            "status": "CASE_NOT_STARTED",
            "reason_code": str(exc),
        }

    write_json(output / "isolation.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ISOLATION_CONFIRMED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
