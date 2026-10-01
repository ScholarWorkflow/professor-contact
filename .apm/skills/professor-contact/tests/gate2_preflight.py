"""Fixed non-acceptance characterization of the shared evaluator and oracle.

Mutation remains in memory and is restored. A rejected counterexample is not
a formal product FAIL. The normal full suite is a separate execution.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

from gate2_evidence import EvidenceResult
import test_contact_targets
import test_gate2_evidence
import test_stage01_caller_contract
import test_codex_native_delegation_contract


REPO_ROOT = Path(__file__).resolve().parents[4]


def run(test):
    return unittest.TextTestRunner(stream=io.StringIO(), resultclass=EvidenceResult).run(test)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def source_snapshot():
    """Hash repository source while ignoring interpreter/runtime by-products."""
    snapshot = {}
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        if '.git' in relative.parts or '__pycache__' in relative.parts:
            continue
        if path.suffix in {'.pyc', '.pyo'}:
            continue
        snapshot[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def main():
    if len(sys.argv) != 2 or Path(sys.argv[1]).exists():
        raise SystemExit('pass exactly one unused output path')

    before = source_snapshot()

    channels = run(unittest.defaultTestLoader.loadTestsFromModule(test_gate2_evidence))
    evaluator_checks_ok = channels.wasSuccessful()
    require(evaluator_checks_ok, f'evaluator channel checks failed: {channels.events}')

    targets = test_contact_targets
    original = targets.mod.select_target
    reads = []

    def wrong_select(root, *args, **kwargs):
        sibling = Path(root) / targets.PROFESSOR_B_DIR / targets.TARGET_NAME
        sibling.read_bytes()
        reads.append(str(targets.PROFESSOR_B_DIR / targets.TARGET_NAME))
        return original(root, *args, **kwargs)

    with mock.patch.object(targets.mod, 'select_target', wrong_select):
        rejection = run(targets.ContactTargetsTests(
            'test_issue64_t1_reselection_reads_only_its_own_professor'))
    discarded_sibling_read_rejected = bool(
        reads and len(rejection.failures) == 1 and not rejection.errors
        and rejection.events and rejection.events[0]['verdict'] == 'FAIL'
    )
    require(discarded_sibling_read_rejected,
            f'sibling-read counterexample was not rejected: {rejection.events}')

    # Wrong input/pending identity may not borrow a valid return example.
    caller = test_stage01_caller_contract
    original_read = caller._read

    def wrong_read(path):
        text = original_read(path)
        if path == caller.STAGE0_AGENT:
            head, tail = text.split('## Input', 1)
            section, rest = tail.split('## ', 1)
            section = section.replace('"professor_dir":', '"display_name":', 1)
            return head + '## Input' + section + '## ' + rest
        return text

    with mock.patch.object(caller, '_read', wrong_read):
        wrong_identity = run(caller.Stage01CallerContractTests(
            'test_issue64_t4_caller_handoff_is_professor_local_transaction_records'))
    wrong_selection_identity_rejected = bool(
        len(wrong_identity.failures) == 1 and not wrong_identity.errors
    )
    require(wrong_selection_identity_rejected,
            f'selection-identity counterexample was not rejected: {wrong_identity.events}')

    routing = test_codex_native_delegation_contract
    original_routing_read = routing.read

    def wrong_child(path):
        text = original_routing_read(path)
        if path == routing.opencode_agent_path('professor-contact-analyzer'):
            before_gate, gate = text.split('## Runtime routing gate (read first)', 1)
            gate = gate.replace('`paper-analysis`', '`wrong-child`', 1)
            return before_gate + '## Runtime routing gate (read first)' + gate
        return text

    with mock.patch.object(routing, 'read', wrong_child):
        wrong_routing = run(routing.CodexNestedDelegatorContractTests(
            'test_opencode_branch_keeps_native_task_semantics'))
    wrong_opencode_child_rejected = bool(
        len(wrong_routing.failures) == 1 and not wrong_routing.errors
    )
    require(wrong_opencode_child_rejected,
            f'wrong-child counterexample was not rejected: {wrong_routing.events}')

    source_files_modified = source_snapshot() != before
    require(not source_files_modified, 'preflight modified repository source files')

    record = {
        'schema_version': 2,
        'evaluator_checks': channels.testsRun,
        'evaluator_checks_ok': evaluator_checks_ok,
        'discarded_sibling_read': {
            'observed': reads,
            'rejected': discarded_sibling_read_rejected,
            'events': rejection.events,
        },
        'wrong_selection_identity_rejected': wrong_selection_identity_rejected,
        'wrong_opencode_child_rejected': wrong_opencode_child_rejected,
        'source_files_modified': source_files_modified,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'evaluator_checks_ok': evaluator_checks_ok,
        'counterexamples_rejected': sum((
            discarded_sibling_read_rejected,
            wrong_selection_identity_rejected,
            wrong_opencode_child_rejected,
        )),
    }))


if __name__ == '__main__':
    main()
