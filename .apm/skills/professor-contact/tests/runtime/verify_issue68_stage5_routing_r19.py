#!/usr/bin/env python3
"""PC68-R1 verifier: professor-local business consumption and root orchestration."""
import argparse
import hashlib
import json
import shlex
from pathlib import Path

import verify_issue68_stage5_routing as base
import verify_issue68_stage5_routing_r13 as final_source


AGENT = base.AGENT
verdict = base.verdict
combine = base.combine
owner_outcome = base.owner_outcome
codex_final_result_source = final_source.codex_final_result_source


ACTIONS = {"stage5-list-inputs", "stage5-partition-choices", "stage5-plan",
           "stage5-rebuild-overview"}
OWNER_OBSERVATION_SCHEMA = "issue-68-test-plan-r25-owner-input-v2"


def command_action(command, manifest):
    """Only a structured executed shell item can supply a stage5 CLI invocation.

    Same structural gate as the base parser. r19 adds
    ``stage5-partition-choices`` to the supported actions, lets ``--owner``
    repeat on the partition call (values accumulate into a list) and pins
    ``--program-root`` to the manifest program root.
    """
    tokens = shlex.split(command)
    if len(tokens) == 3 and Path(tokens[0]).name in ("sh", "bash", "zsh") and tokens[1] in ("-c", "-lc"):
        tokens = shlex.split(tokens[2])
    found = [token for token in tokens if token in ACTIONS]
    if not found:
        return None
    # Compound shell/code expressions are outside this parser's frozen
    # command grammar. Missing observation is never inferred as no call.
    if len(found) != 1 or any(token in (";", "&&", "||", "|") for token in tokens):
        raise ValueError("compound_or_multiple_stage5_commands")
    action = found[0]
    index = tokens.index(action)
    if index == 0 or Path(tokens[index - 1]).name != "contact_state.py":
        raise ValueError("stage5_invocation_script_unobservable")
    tail = tokens[index + 1:]
    if "--help" in tail or "-h" in tail:
        return None
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_unobservable")
    flags = {}
    for offset in range(0, len(tail), 2):
        flag, value = tail[offset], tail[offset + 1]
        if not flag.startswith("--"):
            raise ValueError("stage5_invocation_arguments_unobservable")
        if flag == "--owner":
            flags.setdefault(flag, []).append(value)
            continue
        if flag in flags:
            raise ValueError("stage5_invocation_arguments_unobservable")
        flags[flag] = value
    if flags.get("--program-root") != manifest["program_root"]:
        return {"action": action, "problem": "wrong_program_root"}
    return {"action": action, "flags": flags}


def is_business_surface(text):
    """Loose business-surface recognition over one command text.

    A command text is a consumption or orchestration candidate when it
    references the producer CLI (``contact_state.py``) and any supported
    stage5 action word. Real Codex hosts wrap both inside ``python3 -c`` and
    wrapper compound expressions — the action word then lives inside a quoted
    string, never a standalone token — so this check only decides whether a
    text is worth extracting business objects or output facts from; it never
    parses flags. Strict ``command_action`` parsing stays the only source for
    flag facts.
    """
    if not isinstance(text, str):
        return False
    return "contact_state.py" in text and any(action in text for action in ACTIONS)


def is_owner_business_surface(text):
    """Only professor business commands supply consumed-input evidence."""
    return is_business_surface(text) and any(
        action in text for action in ("stage5-partition-choices", "stage5-plan"))


def consumed_business_objects(stage5_calls):
    """Read one r25 observation and plan result from each actual plan call.

    The only accepted source is the strict JSON envelope emitted by the
    existing owner-input parse action and the original ``stage5-plan`` call
    in the *same* commandExecution. Command text, standalone stdout objects,
    unrelated reads and later file contents are not substitutes. Each call is
    kept as its own row so repeated invocations cannot collapse together.
    """
    rows, seen_call_ids, missing_call_ids = [], set(), []
    plan_calls = []
    for call in stage5_calls:
        if not isinstance(call, dict):
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, {"program_root": _packet_program_root(call)})
        except (ValueError, KeyError, TypeError):
            parsed = None
        action = parsed.get("action") if isinstance(parsed, dict) else _compound_action(command)
        if action == "stage5-plan":
            plan_calls.append(call)
    if not plan_calls:
        return [], verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")

    for call in sorted(plan_calls, key=lambda row: (row.get("start", -1), row.get("end", -1))):
        call_id = call.get("id")
        thread = call.get("thread")
        generation = call.get("generation")
        if not isinstance(call_id, str) or not call_id or call_id in seen_call_ids \
                or not isinstance(thread, str) or not thread \
                or not isinstance(generation, str) or not generation:
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_association_invalid",
                               observed_call_id=call_id, observed_thread=thread,
                               observed_generation=generation)
        seen_call_ids.add(call_id)
        command = call.get("command", "")
        try:
            parsed = command_action(command, {"program_root": _packet_program_root(call)})
        except (ValueError, KeyError, TypeError):
            parsed = None
        action = parsed.get("action") if isinstance(parsed, dict) else _compound_action(command)
        if action != "stage5-plan":
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_step_ambiguous",
                               observed_call_id=call_id)
        output = call.get("output")
        if not isinstance(output, str) or not output.strip():
            missing_call_ids.append(call_id)
            continue
        try:
            envelope = _strict_json_object(output)
        except (ValueError, TypeError):
            # Output with unrelated diagnostics/reads or damaged JSON cannot
            # be interpreted as an input observation.
            if "pc68_actual_input_observation" not in output:
                missing_call_ids.append(call_id)
                continue
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_malformed",
                               observed_call_id=call_id)
        if set(envelope) != {"pc68_actual_input_observation", "stage5_plan", "return_code",
                             "stage5_invocation"}:
            if "pc68_actual_input_observation" not in envelope:
                missing_call_ids.append(call_id)
                continue
            if "stage5_invocation" not in envelope:
                return [], verdict("BLOCKED_OBSERVABILITY", "owner_stage5_invocation_unobservable",
                                   observed_call_id=call_id)
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_shape_invalid",
                               observed_call_id=call_id)
        observation = envelope.get("pc68_actual_input_observation")
        plan = envelope.get("stage5_plan")
        if not isinstance(observation, dict) or observation.get("schema") != OWNER_OBSERVATION_SCHEMA \
                or observation.get("source_step") != "owner_input_json_parse" \
                or observation.get("business_step") != "stage5-plan" \
                or not isinstance(observation.get("object"), dict) \
                or not isinstance(plan, dict) or not isinstance(envelope.get("return_code"), int):
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_shape_invalid",
                               observed_call_id=call_id)
        packet = observation["object"]
        try:
            invocation = _structured_stage5_invocation(envelope["stage5_invocation"])
        except (ValueError, TypeError):
            return [], verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                               observed_call_id=call_id)
        if invocation["action"] != "stage5-plan":
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_step_ambiguous",
                               observed_call_id=call_id)
        pack = packet.get("email_pack")
        program_root = packet.get("program_root")
        if not isinstance(pack, str) or not pack or not isinstance(program_root, str) or not program_root:
            return [], verdict("INVALID_EVIDENCE", "owner_input_observation_identity_missing",
                               observed_call_id=call_id)
        if plan.get("email_pack") not in (None, pack):
            return [], verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                               observed_call_id=call_id, observed_pack=plan.get("email_pack"),
                               observed_input_pack=pack)
        rows.append({"packet": packet, "plan": plan, "invocation": invocation, "call_id": call_id,
                     "thread": thread, "generation": generation,
                     "command": command, "return_code": envelope["return_code"],
                     "start": call.get("start"), "end": call.get("end")})
    if missing_call_ids:
        return [], verdict("BLOCKED_OBSERVABILITY", "owner_actual_input_unobservable",
                           missing_call_ids=missing_call_ids)
    return rows, None


def _packet_program_root(call):
    """Only used to structurally parse direct commands without guessing flags."""
    command = call.get("command", "") if isinstance(call, dict) else ""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ""
    for index, token in enumerate(tokens[:-1]):
        if token == "--program-root":
            return tokens[index + 1]
    # Compound wrappers have no strict flag facts; their output still needs
    # the observation envelope before it can be accepted.
    return ""


def _strict_json_object(text):
    """Parse exactly one JSON object, rejecting duplicate keys and extra text."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict):
        raise ValueError("json_top_level_not_object")
    return value


def _structured_stage5_invocation(value):
    """Parse the exact argv vector recorded at the installed CLI boundary.

    The vector is emitted by the same command wrapper that passes it to the
    existing contact_state.py process. Never recover these facts from the
    shell command string: wrappers and ``python -c`` calls do not expose their
    actual child argv there.
    """
    if not isinstance(value, dict) or set(value) != {"argv"}:
        raise ValueError("stage5_invocation_shape_invalid")
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("stage5_invocation_argv_invalid")
    scripts = [index for index, arg in enumerate(argv)
               if Path(arg).name == "contact_state.py"]
    if len(scripts) != 1:
        raise ValueError("stage5_invocation_script_ambiguous")
    action_index = scripts[0] + 1
    if action_index >= len(argv) or argv[action_index] not in ACTIONS:
        raise ValueError("stage5_invocation_action_invalid")
    action = argv[action_index]
    tail = argv[action_index + 1:]
    if len(tail) % 2:
        raise ValueError("stage5_invocation_arguments_invalid")
    flags = {}
    for offset in range(0, len(tail), 2):
        flag, item = tail[offset], tail[offset + 1]
        if not flag.startswith("--"):
            raise ValueError("stage5_invocation_arguments_invalid")
        if flag == "--owner":
            flags.setdefault(flag, []).append(item)
            continue
        if flag in flags:
            raise ValueError("stage5_invocation_arguments_invalid")
        flags[flag] = item
    return {"action": action, "flags": flags, "argv": list(argv)}


def _choices_summary(observed, expected):
    """Compact machine-readable summary of how consumed choices deviate."""
    summary = {"observed_rows": len(observed) if isinstance(observed, list) else None,
               "expected_rows": len(expected) if isinstance(expected, list) else None}
    if isinstance(observed, list) and isinstance(expected, list):
        summary["changed_row_indexes"] = [index for index in range(max(len(observed), len(expected)))
                                          if index >= len(observed) or index >= len(expected)
                                          or observed[index] != expected[index]]
    else:
        summary["observed_type"] = type(observed).__name__
    return summary


def owner_payload(rows, manifest):
    """Validate every same-call packet and its directly associated plan result."""
    if not rows:
        return None, verdict("BLOCKED_OBSERVABILITY", "owner_business_object_unobservable")
    first = rows[0]
    packet = first["packet"]
    pack = packet["email_pack"]
    owner = next((candidate for candidate in manifest["owners"]
                  if candidate["email_pack"] == pack), None)
    if owner is None:
        return None, verdict("FAIL_PRODUCT", "unexpected_owner_pack", observed_pack=pack)
    if first.get("generation") is None or first.get("thread") is None:
        return None, verdict("INVALID_EVIDENCE", "owner_input_observation_association_invalid")
    if packet.get("program_root") != manifest.get("program_root"):
        return None, verdict("FAIL_PRODUCT", "owner_program_root_changed", observed_pack=pack)
    if str(Path(pack).parent) != owner["professor_dir"]:
        return None, verdict("FAIL_PRODUCT", "owner_professor_directory_changed",
                             observed_pack=pack, observed_professor_dir=str(Path(pack).parent))
    if "professor_dir" in packet and packet["professor_dir"] != owner["professor_dir"]:
        return None, verdict("FAIL_PRODUCT", "owner_professor_directory_changed",
                             observed_pack=pack, observed_professor_dir=packet["professor_dir"])
    if "choices_scope" in packet:
        return None, verdict("FAIL_PRODUCT", "owner_input_carries_choices_scope", observed_pack=pack)
    if "choices" not in packet:
        return None, verdict("FAIL_PRODUCT", "choices_transport_missing", observed_pack=pack)
    if packet["choices"] != owner["expected_choices_rows"]:
        return None, verdict("FAIL_PRODUCT", "owner_bundle_choices_changed", observed_pack=pack,
                             choices_summary=_choices_summary(packet["choices"], owner["expected_choices_rows"]))
    if "email_id" in packet and packet["email_id"] not in owner["email_ids"]:
        return None, verdict("FAIL_PRODUCT", "owner_target_mismatch", observed_pack=pack,
                             observed_email_id=packet["email_id"])
    if packet.get("result") != owner.get("result"):
        return None, verdict("FAIL_PRODUCT", "owner_result_path_changed", observed_pack=pack,
                             observed_result=packet.get("result"))
    if packet.get("mode") != "first":
        return None, verdict("FAIL_PRODUCT", "owner_mode_changed", observed_pack=pack,
                             observed_mode=packet.get("mode"))
    for row in rows:
        flags = row.get("invocation", {}).get("flags", {})
        if flags.get("--email-pack") not in (None, pack):
            return None, verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                                 observed_call_id=row.get("call_id"),
                                 observed_pack=flags.get("--email-pack"))
        if "--choices-scope" in flags:
            return None, verdict("FAIL_PRODUCT", "owner_plan_carries_choices_scope",
                                 observed_call_id=row.get("call_id"))
        if row["packet"] != packet:
            return None, verdict("FAIL_PRODUCT", "owner_input_changed_between_calls",
                                 observed_call_id=row.get("call_id"))
        if row["thread"] != first["thread"] or row["generation"] != first["generation"]:
            return None, verdict("INVALID_EVIDENCE", "owner_input_observation_association_ambiguous",
                                 observed_call_id=row.get("call_id"))
    first_invocation = first.get("invocation")
    if not isinstance(first_invocation, dict) or first_invocation.get("action") != "stage5-plan":
        return None, verdict("INVALID_EVIDENCE", "owner_stage5_invocation_invalid",
                             observed_call_id=first.get("call_id"))
    if any(flag in first_invocation.get("flags", {}) for flag in ("--result", "--choices")):
        return None, verdict("FAIL_PRODUCT", "owner_initial_plan_carries_result_or_choices",
                             observed_call_id=first.get("call_id"))
    text = json.dumps([row["packet"] for row in rows] + [row["plan"] for row in rows],
                      ensure_ascii=False)
    markers = [marker for marker in owner["sibling_exclusions"] if marker in text]
    if markers:
        return None, verdict("FAIL_PRODUCT", "owner_input_contains_sibling_data", observed_pack=pack,
                             observed_markers=markers)
    problem = _verify_owner_plan_package(rows, owner, manifest)
    if problem:
        return None, problem
    return pack, None


def _truncated(value, maximum):
    value = value or ""
    if not isinstance(value, str) or len(value) <= maximum:
        return value
    return value[:maximum] + "…"


def _expected_model_input(email):
    gaps = []
    for gap in email.get("gaps", []):
        gaps.append({
            "gap_id": gap["gap_id"], "item_key": gap["item_key"],
            "paper_title": gap.get("paper_title"), "paper_year": gap.get("paper_year"),
            "quote": _truncated(gap.get("quote"), 300),
            "translation_zh": _truncated(gap.get("translation_zh"), 200),
            "page": gap.get("page"), "status": gap.get("status"),
            "email_use": gap.get("email_use"), "remaining_gap": gap.get("remaining_gap"),
            "completed_part": gap.get("completed_part")
                if gap.get("email_use") == "extension_context_only" else None,
            "evidence": gap.get("evidence"), "confidence": gap.get("confidence"),
        })
    return {
        "idea": email.get("idea"), "direction_ids": email.get("direction_ids") or [],
        "directions": email.get("directions") or [],
        "user_note": _truncated(email.get("user_note"), 800),
        "papers": email.get("papers"), "gaps": gaps,
        "red_lines": email.get("red_lines"),
        "soft_materials": {"positioning": email.get("soft_materials", {}).get("positioning", [])},
        "user_supplement": email.get("user_supplement") or "",
        "allowed_sources": email.get("allowed_sources"),
    }


def _verify_owner_plan_package(rows, owner, manifest):
    """Compare actual structured plan fields with the pre-run owner pack facts."""
    pack_path = owner["email_pack"]
    try:
        raw = Path(pack_path).read_bytes()
        expected_hash = manifest.get("pre_run_hashes", {}).get(pack_path)
        if expected_hash and hashlib.sha256(raw).hexdigest() != expected_hash:
            return verdict("INVALID_EVIDENCE", "owner_fixture_pack_changed", observed_pack=pack_path)
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return verdict("INVALID_EVIDENCE", "owner_fixture_pack_unreadable", observed_pack=pack_path)
    emails = payload.get("emails")
    if not isinstance(emails, list) or any(not isinstance(email, dict) for email in emails):
        return verdict("INVALID_EVIDENCE", "owner_fixture_pack_malformed", observed_pack=pack_path)
    by_id = {email.get("email_id"): email for email in emails}
    for index, observed in enumerate(rows):
        target_id = observed["packet"].get("email_id")
        selected_emails = [by_id[target_id]] if target_id in by_id else emails
        expected_ids = [email.get("email_id") for email in selected_emails]
        plan = observed["plan"]
        if plan.get("email_pack") is not None and plan.get("email_pack") != pack_path:
            return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                           observed_call_id=observed.get("call_id"), observed_pack=plan.get("email_pack"))
        if "emails" in plan and plan.get("emails") != expected_ids:
            return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                           observed_call_id=observed.get("call_id"), observed_emails=plan.get("emails"))
        jobs = plan.get("jobs")
        if index == 0 and (plan.get("status") != "ok" or not isinstance(jobs, list)
                           or observed.get("return_code") != 0):
            return verdict("FAIL_PRODUCT", "owner_initial_plan_changed",
                           observed_call_id=observed.get("call_id"), observed_status=plan.get("status"))
        if index == 0 and (plan.get("template") != observed["packet"].get("template")
                           or plan.get("output_mode") != observed["packet"].get("mode")):
            return verdict("FAIL_PRODUCT", "owner_initial_plan_business_data_changed",
                           observed_call_id=observed.get("call_id"))
        if index == 0:
            professor = owner.get("professor")
            expected_verify = {professor: "needs_recheck:missing"}
            if professor is None or plan.get("verify") != expected_verify \
                    or plan.get("needs_recheck_professors") != [professor]:
                return verdict("FAIL_PRODUCT", "owner_initial_plan_verification_changed",
                               observed_call_id=observed.get("call_id"),
                               observed_verify=plan.get("verify"))
        if jobs is None:
            # Later calls may stop legally at the existing verification gate.
            if plan.get("status") not in {"needs_input", "needs_refresh", "ok"}:
                return verdict("FAIL_PRODUCT", "owner_plan_status_changed",
                               observed_call_id=observed.get("call_id"), observed_status=plan.get("status"))
            continue
        if not isinstance(jobs, list) or len(jobs) != len(emails):
            return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                           observed_call_id=observed.get("call_id"))
        for job in jobs:
            if not isinstance(job, dict) or job.get("kind") != "email":
                return verdict("FAIL_PRODUCT", "owner_plan_business_data_changed",
                               observed_call_id=observed.get("call_id"))
            email_id = job.get("job_id", "").removeprefix("email:")
            email = {row.get("email_id"): row for row in selected_emails}.get(email_id)
            if email is None or job.get("job_id") != "email:" + str(email.get("email_id")):
                return verdict("FAIL_PRODUCT", "owner_plan_email_ids_changed",
                               observed_call_id=observed.get("call_id"), observed_job_id=job.get("job_id"))
            expected = _expected_model_input(email)
            actual = job.get("model_input")
            if not isinstance(actual, dict) or any(key not in actual or actual.get(key) != value
                                                   for key, value in expected.items()):
                return verdict("FAIL_PRODUCT", "owner_plan_business_data_changed",
                               observed_call_id=observed.get("call_id"), observed_email_id=email_id)
    return None


def final_result_rows(texts):
    """Professor rows from the pinned final message's direct report values."""
    return [row for row in _final_report_candidates(texts)
            if "professor_dir" in row and "status" in row and "reason_code" in row]


def _is_overview_result(value):
    """Recognize producer rebuild results from their actual structured shape."""
    if not isinstance(value, dict) or not isinstance(value.get("status"), str):
        return False
    if value["status"] == "ok":
        return {"overview_md", "professors", "emails"} <= set(value)
    return value["status"] in {"needs_decision", "error"} \
        and isinstance(value.get("reason_code"), str) and bool(value["reason_code"])


def _final_report_candidates(texts):
    """Read direct result values; never recurse into history or diagnostics.

    A top-level array contributes its direct objects. A report object may put
    professor rows and the overview result side by side under arbitrary keys.
    One single-object envelope is allowed; grouping key names are not pinned.
    """
    candidates = []
    for text in texts:
        for value in base.json_values(text):
            if isinstance(value, list):
                candidates.extend(row for row in value if isinstance(row, dict))
                continue
            if not isinstance(value, dict):
                continue
            if "professor_dir" in value or _is_overview_result(value):
                candidates.append(value)
                continue
            report = value
            if len(report) == 1:
                nested = next(iter(report.values()))
                if isinstance(nested, dict):
                    report = nested
            for member in report.values():
                if isinstance(member, dict):
                    candidates.append(member)
                elif isinstance(member, list):
                    candidates.extend(row for row in member if isinstance(row, dict))
    return candidates


def _overview_call_result(call):
    """Resolve exactly one result from this call's aggregatedOutput."""
    output = call.get("output")
    if not isinstance(output, str) or not output.strip():
        return None, verdict("BLOCKED_OBSERVABILITY", "root_overview_call_result_unobservable")
    if base.source_malformed([output]):
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_malformed")
    values = base.json_values(output)
    if not values:
        return None, verdict("BLOCKED_OBSERVABILITY", "root_overview_call_result_unobservable")
    results = [value for value in values if _is_overview_result(value)]
    if len(results) > 1:
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_ambiguous")
    if len(results) != 1:
        return None, verdict("INVALID_EVIDENCE", "root_overview_call_result_unattributable")
    return results[0], None


def _receipt_body(item):
    """The frozen receipt body: only the item's ``input_text`` content parts."""
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(part["text"] for part in content if isinstance(part, dict)
                     and part.get("type") == "input_text"
                     and isinstance(part.get("text"), str))


def _final_answer_payload(text, author_path):
    """The strictly shaped Codex child completion payload of one receipt body.

    The frozen receipt body is the three header lines ``Message Type:
    FINAL_ANSWER``, ``Task name: /root`` and ``Sender: <author_path>`` (each
    checked line by line, trailing whitespace tolerated), then the
    ``Payload:`` marker, then exactly one JSON object carrying the result.
    Any other shape — a different message type, a Sender line naming another
    agent, a missing marker or a body that does not parse into one JSON
    object — returns None: such a text is never a consumption receipt.
    """
    if not isinstance(text, str) or not isinstance(author_path, str):
        return None
    lines = text.splitlines()
    expected = ["Message Type: FINAL_ANSWER", "Task name: /root",
                "Sender: " + author_path, "Payload:"]
    if len(lines) <= len(expected):
        return None
    if any(line.rstrip() != want for line, want in zip(expected, lines)):
        return None
    try:
        payload = json.loads("\n".join(lines[len(expected):]).strip())
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def receipt_payload_outcomes(receipt, professor_dir):
    """The one outcome triple one receipt's Payload top level names for one owner.

    Only the strictly shaped FINAL_ANSWER body counts, and the ``Sender:``
    header must equal the receipt's own ``author``. The parsed Payload JSON is
    read at its top level only and never recursively: the object must carry
    ``professor_dir`` equal to this owner's directory as a top-level field and
    the outcome triple comes from the top-level fields alone. A payload whose
    top level names this owner but lacks ``status`` or ``reason_code`` is
    malformed evidence: it contributes no triple and the second return value
    reports the missing field names, so a missing field is never read as a
    ``None`` outcome. A receipt whose top level carries only a nested object
    (a diagnostic wrapper, for example), whose body fails the shape check or
    which names another professor_dir contributes nothing and is never this
    owner's consumption evidence.
    """
    payload = _final_answer_payload(receipt["text"], receipt["author"])
    if payload is None or payload.get("professor_dir") != professor_dir:
        return [], []
    missing = sorted(field for field in ("status", "reason_code") if field not in payload)
    if missing:
        return [], missing
    return [{key: payload[key] for key in ("professor_dir", "status", "reason_code")}], []


def _plan_checks(parsed, manifest, expected_pack):
    flags = parsed["flags"]
    if expected_pack is not None and flags.get("--email-pack") not in (None, expected_pack):
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed", observed_call=parsed.get("command"))
    if "--choices-scope" in flags:
        return verdict("FAIL_PRODUCT", "owner_plan_carries_choices_scope")
    if expected_pack is None:
        return None
    rows, problem = consumed_business_objects([parsed])
    if problem:
        return problem
    observed_pack = rows[0]["packet"].get("email_pack")
    if observed_pack != expected_pack:
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                       observed_call_id=parsed.get("id"), observed_pack=observed_pack)
    if flags.get("--email-pack") not in (None, observed_pack):
        return verdict("FAIL_PRODUCT", "owner_plan_directory_changed",
                       observed_call_id=parsed.get("id"), observed_pack=flags.get("--email-pack"))
    return None


def _partition_payload(output):
    for value in base.json_values(output):
        if isinstance(value, dict) and value.get("status") == "ok":
            return value
    return None


def _owner_projection(entry):
    """One partition owner as {professor_dir, status, choices_rows}.

    The supported output form carries the status nested under ``partition``;
    the flat form describes the same value, so both project identically.
    """
    if not isinstance(entry, dict):
        return {"professor_dir": None, "status": None, "choices_rows": None}
    status = entry.get("status")
    if status is None and isinstance(entry.get("partition"), dict):
        status = entry["partition"].get("status")
    return {"professor_dir": entry.get("professor_dir"), "status": status,
            "choices_rows": entry.get("choices_rows")}


def _partition_rows(payload):
    owners = payload.get("owners")
    if not isinstance(owners, list):
        return None
    return [_owner_projection(entry) for entry in owners]


def _dir_key(row):
    return str(row.get("professor_dir"))


def _compound_action(command):
    """The single supported stage5 action word in a compound command text.

    Compound host expressions carry action words inside quoted strings, so
    strict parsing cannot attribute them; the loose text scan does. Returns
    None when several action words appear — such a text cannot be attributed
    to one orchestration step.
    """
    actions = [action for action in ACTIONS if action in command]
    return actions[0] if len(actions) == 1 else None


def _final_result_role_ambiguity(source_matches, manifest, outcomes=None):
    """Reject one final object that is both the rebuild result and an owner row."""
    for row in source_matches:
        if not isinstance(row, dict):
            continue
        for owner in manifest["owners"]:
            expected = (outcomes or {}).get(owner["email_pack"],
                        dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
            if row.get("professor_dir") != owner["professor_dir"] or \
                    any(field not in row for field in ("status", "reason_code")):
                continue
            reported_owner = {key: row[key] for key in
                              ("professor_dir", "status", "reason_code")}
            if reported_owner == expected:
                return verdict("INVALID_EVIDENCE", "root_final_result_role_ambiguous",
                               observed_result=row, professor_dir=owner["professor_dir"])
    return None


def _early_final_result_role_ambiguity(calls, root, root_texts, manifest, outcomes=None):
    """Find a role collision before invalid owner-status results short-circuit."""
    if base.source_malformed(root_texts):
        return None
    rebuilds = []
    for call in calls:
        if call.get("thread") != root:
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except ValueError:
            if not is_business_surface(command):
                continue
            parsed = None
        if parsed is None:
            if not is_business_surface(command) or "--help" in command:
                continue
            action = _compound_action(command)
        else:
            if parsed.get("problem"):
                continue
            action = parsed.get("action")
        if action == "stage5-rebuild-overview":
            rebuilds.append(call)
    if len(rebuilds) != 1:
        return None
    overview_result, problem = _overview_call_result(rebuilds[0])
    if problem:
        return None
    source_matches = [row for row in _final_report_candidates(root_texts)
                      if row == overview_result]
    return _final_result_role_ambiguity(source_matches, manifest, outcomes)


def runtime_checks(calls, manifest, consumption_points, root_texts, root=None, outcomes=None, owner_threads=None):
    """The r21 root orchestration oracle over executed stage5 calls.

    Discovery must report exactly the fixture owner set and must not emit a
    choices scope; the root must succeed at exactly one partition whose
    per-owner bundles match the manifest partition record and whose
    completion precedes every owner business call; owner plans stay
    bound to their own pack and bundle file and never carry a choices scope;
    exactly one rebuild must run after every owner result was consumed
    (``consumption_points`` are the root's per-child result-consumption
    points, the earliest matching root-thread receipt seqs). The rebuild's
    ``aggregatedOutput`` is the result source, and the pinned final source must
    report that result separately while preserving one consistent consumed
    outcome per owner directory.

    A supported call is recognized on two surfaces. A call whose command
    parses strictly under ``command_action`` keeps every flag fact: only such
    a call can prove the ``--emit-choices-scope``/``--choices-scope``/
    ``--program-root`` facts. A compound command (a ``python3 -c``/wrapper
    preparation whose action words are quoted string fragments, never
    standalone tokens) is recognized by ``is_business_surface`` plus its
    single action word and contributes only its thread attribution and its
    ``aggregatedOutput``: discovery and partition success are judged from the
    output JSON alone. A compound root text carrying several action words
    cannot be attributed to one orchestration step and stays
    BLOCKED_OBSERVABILITY/root_orchestration_ambiguous. A child's compound
    consumption is judged by the packet oracle; on a child thread only a
    strictly parsed partition, or a compound text whose single action word is
    ``stage5-partition-choices``, proves ``partition_executed_by_owner``.
    """
    discovery, partitions, plans, rebuilds = [], [], [], []
    owner_threads = owner_threads or {}
    for call in calls:
        command, thread = call["command"], call.get("thread")
        if root is not None and thread != root and _compound_action(command) == "stage5-rebuild-overview":
            continue
        try:
            parsed = command_action(command, manifest)
        except ValueError as exc:
            if not is_business_surface(command):
                return verdict("BLOCKED_OBSERVABILITY", str(exc))
            parsed = None
        if parsed is None:
            if not is_business_surface(command):
                continue
            if "--help" in command:
                # Help output stays non-evidence, mirroring the strict
                # grammar's --help exclusion for compound texts too.
                continue
            action = _compound_action(command)
            if action is None:
                if root is None or thread == root:
                    return verdict("BLOCKED_OBSERVABILITY", "root_orchestration_ambiguous",
                                   detail=command[:200])
                continue
            if root is not None and thread != root:
                # A child's compound consumption is judged by the packet
                # oracle, never by orchestration flag facts.
                if action == "stage5-partition-choices":
                    return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
                continue
            parsed = {"action": action, "flags": {}, "compound": True}
        if parsed.get("problem"):
            return verdict("FAIL_PRODUCT", parsed["problem"])
        parsed.update(call)
        action, thread = parsed["action"], call.get("thread")
        # Compound calls carry empty flags, so this scope check can only ever
        # fire for a strictly parsed discovery call.
        if action == "stage5-list-inputs" and "--emit-choices-scope" in parsed["flags"]:
            return verdict("FAIL_PRODUCT", "discovery_emits_choices_scope")
        if action == "stage5-plan":
            problem = _plan_checks(parsed, manifest, owner_threads.get(thread))
            if problem:
                return problem
        if root is not None and thread != root:
            if action == "stage5-rebuild-overview":
                continue
            if action == "stage5-partition-choices":
                return verdict("FAIL_PRODUCT", "partition_executed_by_owner")
            if action == "stage5-list-inputs":
                continue
            plans.append(parsed)
            continue
        if action == "stage5-list-inputs":
            discovery.append(parsed)
        elif action == "stage5-partition-choices":
            partitions.append(parsed)
        elif action == "stage5-plan":
            plans.append(parsed)
        else:
            rebuilds.append(parsed)
    if not discovery:
        return verdict("BLOCKED_OBSERVABILITY", "executed_discovery_unobservable")
    expected_packs = {owner["email_pack"] for owner in manifest["owners"]}
    discovered = None
    for call in discovery:
        for value in base.json_values(call.get("output")):
            if isinstance(value, dict) and value.get("status") == "ok" and isinstance(value.get("inputs"), list):
                discovered = {row.get("email_pack"): row.get("status") for row in value["inputs"]}
    if discovered is None:
        return verdict("BLOCKED_OBSERVABILITY", "discovery_result_unobservable")
    if discovered != {**{pack: "ok" for pack in expected_packs}, manifest["invalid_pack"]: "error"}:
        return verdict("FAIL_PRODUCT", "discovery_owner_set_changed")
    successful = [(call, payload) for call in partitions
                  for payload in [_partition_payload(call.get("output"))] if payload is not None]
    if not successful:
        return verdict("FAIL_PRODUCT", "root_partition_not_deterministic", partition_commands=len(partitions))
    if len(successful) > 1:
        return verdict("FAIL_PRODUCT", "multiple_root_partitions")
    partition_call, partition_payload = successful[0]
    observed = _partition_rows(partition_payload)
    expected = [_owner_projection(entry) for entry in manifest["partition"]["owners"]]
    if observed is None or sorted(observed, key=_dir_key) != sorted(expected, key=_dir_key):
        return verdict("FAIL_PRODUCT", "root_partition_changed", observed_owners=observed)
    # r20 ordering fact: the successful root partition must complete before
    # any owner business call starts on a child thread. On a child thread a
    # strictly parsed stage5-list-inputs stays outside the business surface;
    # plan and partition commands count as owner business calls.
    partition_end = partition_call["end"]
    for call in calls:
        if root is None or call.get("thread") == root:
            continue
        command = call.get("command", "")
        try:
            parsed = command_action(command, manifest)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed["action"] in {"stage5-list-inputs", "stage5-rebuild-overview"}:
                continue
        elif not is_owner_business_surface(command):
            continue
        if call["start"] < partition_end:
            return verdict("FAIL_PRODUCT", "owner_business_precedes_partition",
                           observed_call=command[:200])
    if len(rebuilds) > 1:
        return verdict("FAIL_PRODUCT", "multiple_aggregate_rebuilds")
    if not rebuilds:
        return verdict("FAIL_PRODUCT", "aggregate_rebuild_missing")
    if rebuilds[0]["start"] <= max(consumption_points):
        return verdict("FAIL_PRODUCT", "aggregate_precedes_result_consumption")
    overview_result, problem = _overview_call_result(rebuilds[0])
    if problem:
        return problem
    # The pinned final business result source is root's own final message.
    # Grouping names in that source are not part of the result contract; rows
    # and the overview result are associated by their direct object shapes.
    if base.source_malformed(root_texts):
        return verdict("INVALID_EVIDENCE", "root_final_result_malformed")
    candidates = _final_report_candidates(root_texts)
    source_matches = [row for row in candidates if row == overview_result]
    for row in source_matches:
        for owner in manifest["owners"]:
            expected = (outcomes or {}).get(owner["email_pack"],
                        dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
            if row.get("professor_dir") != owner["professor_dir"] or \
                    "status" not in row or "reason_code" not in row:
                continue
            reported_owner = {key: row[key] for key in
                              ("professor_dir", "status", "reason_code")}
            if reported_owner == expected:
                return verdict("INVALID_EVIDENCE", "root_final_result_role_ambiguous",
                               observed_result=row, professor_dir=owner["professor_dir"])
    if len(source_matches) > 1:
        return verdict("INVALID_EVIDENCE", "root_overview_result_ambiguous",
                       observed_candidates=len(source_matches))
    source_match = source_matches[0] if source_matches else None
    owner_candidates = [row for row in candidates if row is not source_match]
    for owner in manifest["owners"]:
        expected = (outcomes or {}).get(owner["email_pack"],
                    dict(owner["expected_result"], professor_dir=owner["professor_dir"]))
        consumed = [row for row in owner_candidates
                    if row.get("professor_dir") == owner["professor_dir"]]
        if not consumed:
            return verdict("BLOCKED_OBSERVABILITY", "root_consumed_result_unobservable")
        if any("status" not in row or "reason_code" not in row for row in consumed):
            return verdict("INVALID_EVIDENCE", "root_final_result_malformed",
                           observed_professor_dir=owner["professor_dir"])
        seen = []
        for row in consumed:
            outcome = {key: row[key] for key in ("professor_dir", "status", "reason_code")}
            if outcome not in seen:
                seen.append(outcome)
        if len(seen) != 1:
            return verdict("FAIL_PRODUCT", "root_consumed_results_conflict", observed_results=seen)
        if seen[0] != expected:
            return verdict("FAIL_PRODUCT", "root_changed_owner_result", observed_result=seen[0])
    reported_overviews = [source_match] if source_match is not None else [
        row for row in owner_candidates
        if _is_overview_result(row) and (
            row.get("status") == "ok"
            or row.get("professor_dir") not in
               {owner["professor_dir"] for owner in manifest["owners"]}
            or any(field in row for field in ("overview_md", "professors", "emails"))
        )
    ]
    if not reported_overviews:
        return verdict("FAIL_PRODUCT", "root_overview_result_unreported")
    if len(reported_overviews) != 1:
        return verdict("INVALID_EVIDENCE", "root_overview_result_ambiguous",
                       observed_candidates=len(reported_overviews))
    if reported_overviews[0] != overview_result:
        return verdict("FAIL_PRODUCT", "root_overview_result_changed",
                       observed_result=reported_overviews[0], expected_result=overview_result)
    return verdict("PASS", owner_pack_set=sorted(expected_packs), rebuild_count=len(rebuilds),
                   partition_executions=1)


def _classify(problem, failures, invalids, blockers):
    bucket = problem.get("verdict")
    if bucket == "FAIL_PRODUCT":
        failures.append(problem)
    elif bucket == "INVALID_EVIDENCE":
        invalids.append(problem)
    else:
        blockers.append(problem)


def _verify_codex_events(response, adapter, manifest):
    status = adapter.get("fixture_status")
    if status in ("INVALID_EVIDENCE", "HARNESS_ERROR", "HARNESS_CONTAMINATION"):
        return verdict("INVALID_EVIDENCE", "shared_adapter_rejected")
    if status == "BLOCKED_DEPENDENCY":
        return verdict("BLOCKED_DEPENDENCY", "shared_adapter_dependency_unavailable")
    if status not in ("FIXTURE_READY", "HARNESS_DISPATCH_UNCONFIRMED", "HARNESS_DISPATCH_MISMATCH"):
        return verdict("INVALID_EVIDENCE", "unknown_shared_adapter_status")
    raw = response.get("output", {})
    root, generation = raw.get("thread_id"), raw.get("runtime_generation")
    events = raw.get("app_server_events")
    if not isinstance(events, list) or not root:
        return verdict("BLOCKED_OBSERVABILITY", "app_server_events_unobservable")
    relations = adapter.get("dispatch", {}).get("thread_relations", [])
    children = {child for edge in relations if edge.get("tool") == "spawnAgent"
                and edge.get("sender_thread_id") == root
                for child in edge.get("receiver_thread_ids", [])}
    if not children:
        return verdict("BLOCKED_OBSERVABILITY", "formal_delegation_unobservable")
    if len(children) != 2:
        return verdict("FAIL_PRODUCT", "wrong_owner_count", formal_children=sorted(children))
    results = {}
    agent_paths, receipts = {}, []
    command_starts, calls, root_texts, business_calls = {}, [], [], {}
    observability_gaps = []
    previous_seq = -1
    for event in events:
        seq = event.get("runtime_seq")
        if not isinstance(seq, int) or seq <= previous_seq or event.get("runtime_generation") != generation:
            return verdict("INVALID_EVIDENCE", "event_order_or_generation_invalid")
        previous_seq = seq
        message = event.get("message", {})
        method, params = message.get("method"), message.get("params", {})
        thread, item = params.get("threadId"), params.get("item", {})
        if item.get("type") == "subAgentActivity":
            # The child_thread_id -> child_agent_path association from the
            # same run's subAgentActivity items (item/started and
            # item/completed both carry it). agentPath is an association key
            # only and never creates formal ownership.
            child_thread, agent_path = item.get("agentThreadId"), item.get("agentPath")
            if isinstance(child_thread, str) and isinstance(agent_path, str):
                known = agent_paths.setdefault(child_thread, [])
                if agent_path not in known:
                    known.append(agent_path)
        if method == "rawResponseItem/completed" and item.get("type") == "message":
            text = base.message_text(item)
            if thread in children and item.get("role") == "assistant":
                results.setdefault(thread, []).append(text)
            elif thread == root and item.get("role") == "assistant":
                root_texts.append(text)
        if method == "rawResponseItem/completed" and item.get("type") == "agent_message" \
                and thread == root and item.get("recipient") == "/root" \
                and params.get("turnId") == raw.get("turn_id"):
            # The only root result-consumption surface: a current-turn
            # root-thread agent_message receipt. The official V2 wait item's
            # pairing fields are always empty and its message is only wait
            # status text, so collabAgentToolCall wait items are never parsed
            # as consumption evidence; each receipt body must still parse as
            # the frozen FINAL_ANSWER shape before it counts.
            receipts.append({"seq": seq, "author": item.get("author"),
                             "text": _receipt_body(item)})
        if thread in children | {root} and item.get("type") == "commandExecution":
            item_id = (thread, item.get("id"))
            if method == "item/started":
                command_starts[item_id] = seq
            elif method == "item/completed":
                if item_id not in command_starts:
                    # r24: a completed commandExecution without a started
                    # record is an observability gap, not an early terminal.
                    # The command yields no call and the scan continues, so a
                    # sibling child's proven failure keeps its precedence.
                    observability_gaps.append(("command_start_unobservable", thread, seq))
                    continue
                call = {"id": item.get("id"), "start": command_starts[item_id], "end": seq,
                        "command": item.get("command", ""), "output": item.get("aggregatedOutput", ""),
                        "thread": thread, "generation": generation}
                calls.append(call)
                if thread in children:
                    business_calls.setdefault(thread, []).append(call)
    failures, invalids, blockers = [], [], []
    assigned, outcomes, consume_points = {}, {}, {}
    for child in sorted(children):
        stage5_calls = [call for call in business_calls.get(child, [])
                        if is_owner_business_surface(call.get("command", ""))]
        rows, problem = consumed_business_objects(stage5_calls)
        if not problem:
            pack, problem = owner_payload(rows, manifest)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        if pack in assigned:
            failures.append(verdict("FAIL_PRODUCT", "duplicate_owner_pack"))
            continue
        assigned[pack] = child
        owner = next(owner for owner in manifest["owners"] if owner["email_pack"] == pack)
        outcome, problem = base.owner_outcome(results.get(child, []), owner)
        if problem:
            _classify(problem, failures, invalids, blockers)
            continue
        # The child_thread_id -> agent_path mapping must be unique before any
        # receipt can be attributed: with no agent path the child can never be
        # bound to a receipt author, and with more than one distinct agentPath
        # the formal child to author association is ambiguous, so the evidence
        # itself is damaged no matter how correct one surviving path's own
        # receipt looks. Only a unique mapping may bind receipts to that one
        # agent path author.
        paths = agent_paths.get(child, [])
        if len(paths) != 1:
            if not paths:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_consumption_unobservable",
                                        detail="missing_agent_path_mapping"))
            else:
                invalids.append(verdict("INVALID_EVIDENCE",
                                        "child_agent_path_mapping_ambiguous",
                                        detail=list(paths)))
            continue
        matched, malformed = [], []
        for receipt in receipts:
            if receipt["author"] != paths[0]:
                continue
            receipt_own, missing_fields = receipt_payload_outcomes(receipt, owner["professor_dir"])
            if missing_fields:
                # A receipt naming this owner whose Payload top level lacks
                # status/reason_code is malformed evidence, never a changed
                # payload: it counts as no legal receipt.
                malformed.append(missing_fields)
                continue
            if receipt_own:
                matched.append((receipt["seq"], receipt_own))
        if not matched:
            if malformed:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_receipt_malformed",
                                        detail=sorted({field for fields in malformed
                                                       for field in fields})))
            else:
                blockers.append(verdict("BLOCKED_OBSERVABILITY",
                                        "root_result_consumption_unobservable"))
            continue
        observed = []
        for _, receipt_own in matched:
            for candidate in receipt_own:
                if candidate not in observed:
                    observed.append(candidate)
        if len(observed) != 1:
            invalids.append(verdict("INVALID_EVIDENCE", "root_result_receipt_ambiguous",
                                    observed_outcomes=observed))
            continue
        if observed[0] != outcome:
            failures.append(verdict("FAIL_PRODUCT", "root_receipt_payload_changed",
                                    observed_result=observed[0], expected_result=outcome))
            continue
        consume_points[child] = min(seq for seq, _ in matched)
        outcomes[pack] = outcome
    if failures and not invalids and not blockers and all(
            problem.get("reason_code") == "owner_verification_boundary_bypassed"
            for problem in failures):
        role_problem = _early_final_result_role_ambiguity(
            calls, root, root_texts, manifest, outcomes)
        if role_problem:
            return role_problem
    for bucket in (failures, invalids, blockers):
        if bucket:
            return bucket[0]
    if raw.get("termination_reason") != "completed":
        return verdict("BLOCKED_DEPENDENCY", "root_turn_not_completed")
    result = runtime_checks(calls, manifest, list(consume_points.values()), root_texts, root=root,
                            outcomes=outcomes,
                            owner_threads={child: pack for pack, child in assigned.items()})
    result["identity_diagnostics"] = adapter.get("dispatch", {}).get("agent_identity", {})
    # Unified terminal precedence: a proven FAIL/INVALID keeps its precedence
    # over collected observability gaps, which affect only otherwise-clean runs.
    if result.get("verdict") in ("FAIL_PRODUCT", "INVALID_EVIDENCE"):
        return result
    if observability_gaps:
        return verdict("BLOCKED_OBSERVABILITY", "command_start_unobservable",
                       detail=[list(gap) for gap in observability_gaps])
    return result


def _judge_with_final_source(judge, final_text, *args):
    """Run the frozen r19 orchestration oracle with one machine-selected root text."""
    original = runtime_checks

    def pinned(calls, manifest, consumption_points, _root_texts, **kwargs):
        return original(calls, manifest, consumption_points, [final_text], **kwargs)

    globals()["runtime_checks"] = pinned
    try:
        return judge(*args)
    finally:
        globals()["runtime_checks"] = original


def verify_codex(response, adapter, manifest):
    final_text, problem = codex_final_result_source(response)
    if problem:
        return problem
    return _judge_with_final_source(_verify_codex_events, final_text, response, adapter, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--shared-verdict", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.host != "codex":
        parser.error("r19 verifies the codex host only")
    try:
        manifest = json.loads(args.manifest.read_text())
        shared = json.loads(args.shared_verdict.read_text())
        result = verify_codex(json.loads(args.events.read_text()), shared, manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = verdict("INVALID_EVIDENCE", "unreadable_or_malformed_evidence", detail=str(exc))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
