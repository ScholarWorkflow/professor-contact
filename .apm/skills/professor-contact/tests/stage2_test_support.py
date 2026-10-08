"""Shared real-preflight prerequisites for preserved business tests."""

from pathlib import Path


def run_bound_stage2_plan(run_cli, facts_path: Path):
    from stage2_upstream_fixture import run_bound_stage2_plan as real_plan
    return real_plan(run_cli, facts_path)
