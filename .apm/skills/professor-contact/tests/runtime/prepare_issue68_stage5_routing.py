#!/usr/bin/env python3
"""Prepare PC68-R1 business input; precheck with the installed producer CLI."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
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
    choices, raw_results, owner_rows, owner_args = [], {}, {}, []
    for index, row in enumerate(fixture["rows"]):
        pack = fixture["packs"][row["professor"]]
        canonical_dir = str(Path(row["professor_dir"]).resolve())
        choice = dict(helpers.issue59_choices(row["email_id"]),
                      professor_dir=canonical_dir, transport_sentinel=f"owner-{index}")
        choices.append(choice)
        owner_rows[index] = choice
        owner_args += ["--owner", str(pack)]
        result = helpers.issue59_write_results(program_root, f"raw-{index}.json", [row["email_id"]])
        raw_results[canonical_dir] = str(result)
    choices.append({"email_id": "unselected::D::I", "transport_sentinel": "noise"})
    broken = program_root / "教授研究" / "Z分野" / "无效样例" / helpers.contact_state.EMAIL_PACK
    broken.parent.mkdir(parents=True)
    broken.write_text(helpers.ISSUE59_MALFORMED_JSON, encoding="utf-8")
    canonical_choices = output_dir / "canonical-choices.json"
    write_json(canonical_choices, choices)
    # The root partitions the raw multi-professor choices once through the
    # installed deterministic entry; each owner later receives only its own
    # bundle rows from this partition, never the raw object or sibling data.
    partition_out = output_dir / "partition-bundles.json"
    partition = subprocess.run([sys.executable, str(installed_script), "stage5-partition-choices",
                                "--program-root", str(program_root), "--choices", str(canonical_choices),
                                *owner_args, "--out", str(partition_out)],
                               capture_output=True, text=True, check=False)
    (output_dir / "root-partition.stdout.json").write_text(partition.stdout, encoding="utf-8")
    (output_dir / "root-partition.stderr.txt").write_text(partition.stderr, encoding="utf-8")
    (output_dir / "root-partition.exit-code.txt").write_text(str(partition.returncode) + "\n")
    partition_payload = json.loads(partition.stdout)
    if partition.returncode != 0 or partition_payload.get("status") != "ok" \
            or len(partition_payload.get("owners", [])) != len(fixture["rows"]):
        raise ValueError(f"root partition did not answer one ok payload: {partition_payload}")
    bundle_rows = {}
    for index, row in enumerate(fixture["rows"]):
        canonical_dir = str(Path(row["professor_dir"]).resolve())
        entry = next((item for item in partition_payload["owners"]
                      if item.get("professor_dir") == canonical_dir), None)
        if entry is None:
            raise ValueError(f"owner {index} missing from the partition output: {partition_payload}")
        rows = entry.get("choices_rows")
        if entry.get("partition", {}).get("status") != "ok" or rows != [owner_rows[index]]:
            raise ValueError(f"owner {index} partition bundle deviates from the constructed rows: {entry}")
        bundle_rows[index] = rows
        write_json(output_dir / f"owner-{index}-bundle-choices.json", rows)
    owners = []
    for index, row in enumerate(fixture["rows"]):
        pack = fixture["packs"][row["professor"]]
        canonical_dir = str(Path(row["professor_dir"]).resolve())
        result = raw_results[canonical_dir]
        initial = subprocess.run([sys.executable, str(installed_script), "stage5-plan",
                                  "--program-root", str(program_root), "--email-pack", str(pack),
                                  "--template", str(template), "--mode", "first"],
                                 capture_output=True, text=True, check=False)
        (output_dir / f"owner-{index}-initial-plan.stdout.json").write_text(initial.stdout, encoding="utf-8")
        (output_dir / f"owner-{index}-initial-plan.stderr.txt").write_text(initial.stderr, encoding="utf-8")
        (output_dir / f"owner-{index}-initial-plan.exit-code.txt").write_text(str(initial.returncode) + "\n")
        initial_payload = json.loads(initial.stdout)
        if initial.returncode != 0 or initial_payload.get("status") != "ok" \
                or initial_payload.get("verify", {}).get(row["professor"]) != "needs_recheck:missing":
            raise ValueError(f"owner {index} initial verification boundary changed: {initial_payload}")
        run = subprocess.run([sys.executable, str(installed_script), "stage5-plan",
                              "--program-root", str(program_root), "--email-pack", str(pack),
                              "--result", str(result), "--choices",
                              str(output_dir / f"owner-{index}-bundle-choices.json"),
                              "--template", str(template), "--mode", "first"],
                             capture_output=True, text=True, check=False)
        (output_dir / f"owner-{index}-plan.stdout.json").write_text(run.stdout, encoding="utf-8")
        (output_dir / f"owner-{index}-plan.stderr.txt").write_text(run.stderr, encoding="utf-8")
        payload = json.loads(run.stdout)
        (output_dir / f"owner-{index}-plan.exit-code.txt").write_text(str(run.returncode) + "\n")
        if payload.get("status") != "needs_refresh" or run.returncode != 2:
            raise ValueError(f"owner {index} did not stop at the frozen verification gate: {payload}")
        siblings = []
        for other, other_row in enumerate(fixture["rows"]):
            if other == index:
                continue
            siblings += [str(fixture["packs"][other_row["professor"]].resolve()),
                         str(Path(other_row["professor_dir"]).resolve()),
                         other_row["email_id"], f"owner-{other}"]
        siblings.append("choices_scope")
        owners.append({"professor": row["professor"], "professor_dir": canonical_dir,
                       "email_pack": str(pack.resolve()), "email_ids": [row["email_id"]],
                       "expected_choices_rows": deepcopy(bundle_rows[index]),
                       "expected_bundle_file": f"owner-{index}-bundle-choices.json",
                       "sibling_exclusions": siblings,
                       "expected_result": payload, "initial_plan": initial_payload, "result": str(result)})
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
                "expected_choices": choices,
                "partition": {"bundle_file": "partition-bundles.json",
                              "owners": [{"professor_dir": owner["professor_dir"], "status": "ok",
                                          "choices_rows": deepcopy(owner["expected_choices_rows"])}
                                         for owner in owners]},
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
