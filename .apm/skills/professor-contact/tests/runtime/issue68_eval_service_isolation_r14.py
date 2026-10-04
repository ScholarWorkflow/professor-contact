#!/usr/bin/env python3
"""Shared r14 verifier for the persistent Codex eval service storage boundary."""
import subprocess
import tomllib
from pathlib import Path


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
    production_default = (Path.home() / ".codex").resolve()
    if codex_home == production_default:
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
    sqlite_source = (
        "config.sqlite_home"
        if sqlite_config
        else ("CODEX_SQLITE_HOME" if sqlite_env else "CODEX_HOME fallback")
    )
    log_source = "config.log_dir" if log_config else "CODEX_HOME-derived default"

    return {
        "status": "ISOLATION_CONFIRMED",
        "service_pid": pid,
        "service_cwd": service["cwd"],
        "codex_home": str(codex_home),
        "production_default_codex_home": str(production_default),
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
            "effective_path": str(log_config) if log_config else None,
            "source": log_source,
            "inside_test_codex_home": True if log_config is None else is_within(log_config, codex_home),
        },
    }
