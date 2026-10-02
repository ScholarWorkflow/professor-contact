#!/usr/bin/env python3
"""Prepare PC68-R1 business input; precheck with the installed producer CLI."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(program_root, installed_script, output_dir):
    spec = importlib.util.spec_from_file_location("issue68_fixture_builders", HERE.parent / "test_contact_state.py")
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    program_root = Path(program_root).resolve()
    output_dir = Path(output_dir).resolve()
    program_root.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture = helpers.write_issue59_stage5_fixture(program_root, [
        {"professor": helpers.ISSUE59_PROFESSOR, "evidence": "none", "verified": "missing"},
        {"professor": helpers.ISSUE59_OTHER_PROFESSOR, "evidence": "none", "verified": "missing"}])
    # This is user business input, not a replacement agent or runtime override.
    template = program_root / "synthetic-template.md"
    template.write_text("{{大学}}／{{研究科}}／{{先生名}}先生\n{{出身校}} {{氏名}}\n"
                        "{{入学年度}} {{入学月}} {{専攻}} {{学位}}\n{{兴趣段}}\n{{未来志向}}\n"
                        "{{学習中}}\n{{志望}}", encoding="utf-8")
    owners, choices, scope, raw_results = [], [], {}, {}
    for index, row in enumerate(fixture["rows"]):
        pack = fixture["packs"][row["professor"]]
        canonical_dir = str(Path(row["professor_dir"]).resolve())
        choice = dict(helpers.issue59_choices(row["email_id"]),
                      professor_dir=canonical_dir, transport_sentinel=f"owner-{index}")
        choices.append(choice)
        scope[canonical_dir] = [row["email_id"]]
        result = helpers.issue59_write_results(program_root, f"raw-{index}.json", [row["email_id"]])
        raw_results[canonical_dir] = str(result)
        run = subprocess.run([sys.executable, str(installed_script), "stage5-plan",
                              "--program-root", str(program_root), "--email-pack", str(pack),
                              "--result", str(result), "--template", str(template), "--mode", "first"],
                             capture_output=True, text=True, check=False)
        (output_dir / f"owner-{index}-plan.stdout.json").write_text(run.stdout, encoding="utf-8")
        (output_dir / f"owner-{index}-plan.stderr.txt").write_text(run.stderr, encoding="utf-8")
        payload = json.loads(run.stdout)
        (output_dir / f"owner-{index}-plan.exit-code.txt").write_text(str(run.returncode) + "\n")
        if payload.get("status") != "needs_refresh" or run.returncode != 2:
            raise ValueError(f"owner {index} did not stop at the frozen verification gate: {payload}")
        owners.append({"professor": row["professor"], "professor_dir": canonical_dir,
                       "email_pack": str(pack.resolve()), "email_ids": [row["email_id"]],
                       "expected_result": payload, "result": str(result)})
    choices.append({"email_id": "unselected::D::I", "transport_sentinel": "noise"})
    broken = program_root / "教授研究" / "Z分野" / "无效样例" / helpers.contact_state.EMAIL_PACK
    broken.parent.mkdir(parents=True)
    broken.write_text(helpers.ISSUE59_MALFORMED_JSON, encoding="utf-8")
    write_json(output_dir / "canonical-choices.json", choices)
    write_json(output_dir / "expected-scope.json", scope)
    business = {"choices": choices, "mode": "first", "template": str(template),
                "raw_results_by_professor_dir": raw_results}
    prompt = (HERE / "prompts" / "issue68-stage5-root.txt").read_text(encoding="utf-8")
    prompt = prompt.replace("{{PROGRAM_ROOT}}", str(program_root)).replace(
        "{{BUSINESS_INPUT}}", json.dumps(business, ensure_ascii=False))
    (output_dir / "root-prompt.txt").write_text(prompt, encoding="utf-8")
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(program_root.rglob("*")) if p.is_file()}
    manifest = {"schema": 1, "case": "PC68-R1", "program_root": str(program_root),
                "owners": owners, "invalid_pack": str(broken.resolve()),
                "expected_choices": choices, "expected_scope": scope,
                "expected_aggregate_rows": 0, "pre_run_hashes": hashes,
                "manual_patch": "no"}
    write_json(output_dir / "fixture-manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--installed-script", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.program_root, args.installed_script, args.output_dir)


if __name__ == "__main__":
    main()
