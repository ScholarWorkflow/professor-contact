#!/usr/bin/env python3
"""Prepare PC68-R1 business input and independent synthetic expectations."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Fixed test specification. The owner binding is an independent oracle for
# this synthetic request; never derive it from stage5-partition-choices.
EXPECTED_OWNERS = (
    {
        "professor": "試験 教授",
        "email_id": "試験 教授::DIR00001::DIR00001_1",
        "transport_sentinel": "owner-0",
        "choice": {
            "first_choice": False,
            "signature_name": "試験 太郎",
            "learning": "比較手法の基礎知識の習得",
        },
    },
    {
        "professor": "佐藤 花子",
        "email_id": "佐藤 花子::DIR00001::DIR00001_1",
        "transport_sentinel": "owner-1",
        "choice": {
            "first_choice": False,
            "signature_name": "試験 太郎",
            "learning": "比較手法の基礎知識の習得",
        },
    },
)


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
    fixture_rows = {row["professor"]: row for row in fixture["rows"]}
    expected_professors = {spec["professor"] for spec in EXPECTED_OWNERS}
    if set(fixture_rows) != expected_professors:
        raise ValueError(f"synthetic fixture owners changed: {sorted(fixture_rows)}")

    choices, raw_results, owner_specs = [], {}, []
    for spec in EXPECTED_OWNERS:
        row = fixture_rows[spec["professor"]]
        if row["email_id"] != spec["email_id"]:
            raise ValueError(f"synthetic fixture email id changed for {spec['professor']}: {row['email_id']}")
        pack = fixture["packs"][spec["professor"]]
        canonical_dir = str(Path(row["professor_dir"]).resolve())
        expected_row = {
            "email_id": spec["email_id"],
            **deepcopy(spec["choice"]),
            "professor_dir": canonical_dir,
            "transport_sentinel": spec["transport_sentinel"],
        }
        choices.append(deepcopy(expected_row))
        result = helpers.issue59_write_results(
            program_root, f"raw-{len(owner_specs)}.json", [spec["email_id"]])
        raw_results[canonical_dir] = str(result)
        owner_specs.append({"spec": spec, "row": row, "pack": pack,
                            "professor_dir": canonical_dir,
                            "expected_choices_rows": [expected_row],
                            "result": str(result)})
    choices.append({"email_id": "unselected::D::I", "transport_sentinel": "noise"})
    broken = program_root / "教授研究" / "Z分野" / "无效样例" / helpers.contact_state.EMAIL_PACK
    broken.parent.mkdir(parents=True)
    broken.write_text(helpers.ISSUE59_MALFORMED_JSON, encoding="utf-8")
    canonical_choices = output_dir / "canonical-choices.json"
    write_json(canonical_choices, choices)
    owners = []
    for index, owner_spec in enumerate(owner_specs):
        spec = owner_spec["spec"]
        row = owner_spec["row"]
        pack = owner_spec["pack"]
        canonical_dir = owner_spec["professor_dir"]
        result = owner_spec["result"]
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
                              "--result", str(result),
                              "--template", str(template), "--mode", "first"],
                             capture_output=True, text=True, check=False)
        (output_dir / f"owner-{index}-plan.stdout.json").write_text(run.stdout, encoding="utf-8")
        (output_dir / f"owner-{index}-plan.stderr.txt").write_text(run.stderr, encoding="utf-8")
        payload = json.loads(run.stdout)
        (output_dir / f"owner-{index}-plan.exit-code.txt").write_text(str(run.returncode) + "\n")
        if payload.get("status") != "needs_refresh" or run.returncode != 2:
            raise ValueError(f"owner {index} did not stop at the frozen verification gate: {payload}")
        siblings = []
        for other_spec in owner_specs:
            other = EXPECTED_OWNERS.index(other_spec["spec"])
            other_row = other_spec["row"]
            if other == index:
                continue
            siblings += [str(other_spec["pack"].resolve()),
                         other_spec["professor_dir"],
                         other_row["email_id"], f"owner-{other}"]
        siblings.append("choices_scope")
        owners.append({"professor": spec["professor"], "professor_dir": canonical_dir,
                       "email_pack": str(pack.resolve()), "email_ids": [row["email_id"]],
                       "expected_choices_rows": deepcopy(owner_spec["expected_choices_rows"]),
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
                "partition": {"owners": [{"professor_dir": owner["professor_dir"], "status": "ok",
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
