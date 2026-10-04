"""Issue #66 deterministic acceptance cases (Gate 2 record issue-66-gate2-r10).

Stage 3 must give every professor an independent formal state: stage3-finalize
commits only the current professor (local Markdown installed first, candidate
state last as the single commit marker) and never touches program-level
state; the program overview is a derived projection rebuilt by
stage3-rebuild-overview from committed states alone, with projection-local
manual-edit protection and strict legacy identity migration owned by the
candidate-state compatibility layer.

Proof conventions (per the frozen Gate 2 record): no-write / rollback /
bytes / absence claims read the target files directly; low-level open and
os.replace wrappers only record or gate real calls and never replace return
values or mock the owner under test; synchronization uses events, never
sleeps.  Reused fixtures: the repo BaseEnv pipeline and the cross-direction
group builder from test_stage3_direction_groups.
"""
import builtins
import contextlib
import inspect
import io
import json
import os
import re
import shutil
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

from test_stage2_resolved_direction import (
    parse, quote_id, run_cli, write_json)
from test_stage3_direction_groups import (
    PROFESSOR, Stage3DirectionGroupBase, contact_state, result_file)

_SCRIPT = Path(__file__).parents[1] / "scripts" / "contact_state.py"
SKILL_PATH = Path(__file__).resolve().parents[4] / ".apm" / "skills" / \
    "professor-contact" / "SKILL.md"
AGENT_PATH = Path(__file__).resolve().parents[4] / ".apm" / "agents" / \
    "professor-contact-idea-generator.agent.md"
WFREF_PATH = Path(__file__).resolve().parents[4] / ".apm" / "skills" / \
    "professor-contact" / "docs" / "workflow-reference.md"

CANDIDATE_STATE = "套磁候选状态.json"
CANDIDATES_MD = "套磁想法候选.md"
CANDIDATES_OVERVIEW = "套磁想法候选总览.md"
PROJECTIONS_FILE = "_contact_projections.json"
CROSS_GROUP_ARG = '[["dir_A","dir_B"]]'
CROSS_GID = contact_state.cross_group_id(["dir_A", "dir_B"])
SECOND_PROFESSOR = "対照 教授"

# Twin-professor quotes: same display name / direction IDs / group ID as the
# base fixture, different canonical professor directory (issue #66 R66-4).
TWIN_QUOTES = {
    "T1": "Future work will extend the twin shared method to batch inputs.",
    "T2": "Future work will benchmark the twin signal pipeline at scale.",
    "T3": "Future work will deploy the twin sensor network citywide.",
}


def call_runner(*argv):
    """Run the deterministic runner in-process; returns (payload, exit_code).

    Used only where low-level wrappers must observe the real call window;
    the subprocess CLI surface stays covered by the run_cli-based cases.
    """
    buffer = io.StringIO()
    old_argv = sys.argv
    code = 0
    try:
        sys.argv = ["contact_state.py", *[str(a) for a in argv]]
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(io.StringIO()):
            try:
                contact_state.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = old_argv
    try:
        return json.loads(buffer.getvalue()), code
    except json.JSONDecodeError:
        return None, code


class OpenRecorder:
    """Record the absolute path of every real low-level file open.

    The wrappers only forward: return values, errors and buffering are the
    real ones, so the record is a read log, not a substitute for the owner.
    """

    def __init__(self):
        self.opened = []

    @staticmethod
    def _normalize(path):
        return os.path.realpath(os.path.abspath(str(path)))

    def __enter__(self):
        self.opened = []
        recorder = self
        orig_open = builtins.open
        orig_io_open = io.open
        orig_os_open = os.open

        def wrapped_open(file, *args, **kwargs):
            recorder.opened.append(recorder._normalize(file))
            return orig_open(file, *args, **kwargs)

        def wrapped_os_open(path, *args, **kwargs):
            recorder.opened.append(recorder._normalize(path))
            return orig_os_open(path, *args, **kwargs)

        self._orig = (orig_open, orig_io_open, orig_os_open)
        # pathlib.Path.open resolves through io.open, not builtins.open, so
        # both bindings must be wrapped to see every real text/binary open.
        builtins.open = wrapped_open
        io.open = wrapped_open
        os.open = wrapped_os_open
        return self

    def __exit__(self, *exc_info):
        builtins.open, io.open, os.open = self._orig
        return False

    def was_opened(self, path):
        return self._normalize(path) in self.opened


@contextlib.contextmanager
def gated_os_replace(predicate, action):
    """Wrap os.replace: matching installs are owned by `action(real, src, dst)`.

    The wrapper hands the real os.replace to the action, which decides whether
    to perform it, block around it, or raise instead; non-matching calls are
    forwarded untouched.
    """
    real = os.replace

    def wrapped(src, dst, *args, **kwargs):
        if predicate(os.path.realpath(os.path.abspath(str(src))),
                     os.path.realpath(os.path.abspath(str(dst)))):
            return action(real, src, dst)
        return real(src, dst)

    with mock.patch("os.replace", wrapped):
        yield


@contextlib.contextmanager
def failing_unlink(predicate):
    """Wrap os.unlink so matching cleanup targets raise a synthetic OSError."""
    real = os.unlink

    def wrapped(path, *args, **kwargs):
        if predicate(os.path.realpath(os.path.abspath(str(path)))):
            raise OSError("synthetic cleanup unlink failure")
        return real(path, *args, **kwargs)

    with mock.patch("os.unlink", wrapped):
        yield


# -- S3-DOC-1 static judgment helpers (issue-66 gate2 r15 revision) ---------
#
# The agent document is prose, so the binding branch has to be judged on the
# clause structure instead of on marker substrings: a document that demands a
# non-empty fingerprint unconditionally, or that reads the fingerprint from the
# finalize response, must be rejected even though it still carries every marker
# string.  The helpers below derive that disposition from the text itself.

_STEP3_START = re.compile(r"\*\*finalize 指纹绑定检查（")
_BRANCH_WITH_PROFILE = re.compile(
    r"(?:存在|有)[^。；\n]{0,60}?profile[^。；\n]{0,8}时")
_BRANCH_NO_PROFILE = re.compile(r"(?:无|没有|未)[^。；\n]{0,12}profile")
_CLAUSE_SPLIT = re.compile(r"[。；\n]+")
_CANCEL_CLAUSE_SPLIT = re.compile(r"[，。；\n]+")
_CLOSE_REFS = ("该状态文件", "该状态", "其中", "它", "状态文件")
_STATE_SOURCE = re.compile(r"state_path|状态文件")
_BIND_FIELD = re.compile(r"profile_fingerprint")
# A read of the field from the finalize response, as opposed to the frozen
# rule's denial that the response carries it at all.
_RESPONSE_FIELD_SOURCE = re.compile(
    r"读取[^。；\n]{0,20}返回的[^。；\n]{0,6}`?profile_fingerprint|"
    r"用返回值中的[^。；\n]{0,6}`?profile_fingerprint|"
    r"finalize[^。；\n]{0,12}返回的[^。；\n]{0,6}`?profile_fingerprint")
_UNCONDITIONAL = re.compile(r"^\s*(?:这一条|本条|本命令的[^，。；\n]{0,8}|其)?\s*必须")
_MUST_NONEMPTY = re.compile(r"必须[^。；\n]{0,20}非空")
_STOP_VERB = re.compile(r"立即(?:停止|结束)")
_NULL_VALUE = re.compile(r"`?null`?")
_ALLOW_CONTINUE = re.compile(
    r"不报错|不停止|不阻断|合法结果|继续|允许[^。；\n]{0,8}空")
# "null is a legal result" may be stated with the null value late in the
# clause; the prohibition on stopping arrives in a following sentence.
_NULL_IS_LEGAL = re.compile(r"`?null`?[^。；\n]{0,20}是[^。；\n]{0,8}合法")
_NO_PROFILE_STOP_WORD = re.compile(r"(?:一律|必须)停|立即(?:停止|结束)")
_NULL_DEMAND = re.compile(
    r"`?profile_fingerprint`?[^。；\n]{0,30}(?:必须|非空)|"
    r"必须[^。；\n]{0,20}非空")
_PROFILE_SCOPE = re.compile(r"profile[^。；\n]{0,12}(?:时|存在|有)|仅[^。；\n]{0,8}profile")
_BIND_FAIL_MARKER = "profile_fingerprint_binding_failed"
_EARLY_STOP_BEFORE_WRITE = re.compile(
    r"(?:之前|早于|停在)[^。；\n]{0,16}(?:写|落盘)[^。；\n]{0,20}result")
_READ_FAIL_STOP = re.compile(r"读取失败[^。；\n]{0,20}(?:立即)?(?:停止|结束|error)")
# The wording that carries the read-failure stop point, located by pattern so
# no single sentence is frozen as the acceptance wording.
_READ_FAIL_WORDING = re.compile(r"状态文件读取失败(?:或不一致)?")
# The committed fingerprint has to be compared with the plan fingerprint and a
# mismatch has to stop the child (issue-66 gate2 revision 2).  The judgment
# works on the demand's semantics: a cancelled comparison is not a
# requirement, whether the cancellation sits before or after the comparison
# wording ("but the run need not compare the two fingerprints").
_CONCORDANCE_SENTENCE = re.compile(
    r"(?:与|跟|同)[^。；\n]{0,20}(?:plan|计划)[^。；\n]{0,60}?(?:一致|同一|相同)|"
    r"其[^。；\n]{0,6}(?:与|跟|同)[^。；\n]{0,12}(?:plan|计划)|"
    r"(?:比较|比对|核对)[^。；\n]{0,16}(?:plan|计划)")
# The comparison topic (committed fingerprint versus plan fingerprint), used to
# read a cancellation sentence even when it carries no agreement wording.
_COMPARISON_TOPIC = re.compile(
    r"(?:比较|比对|核对)[^。；\n]{0,16}(?:plan|计划)|"
    r"(?:plan|计划)[^。；\n]{0,16}(?:指纹|fingerprint)")
_CANCEL_WORDS = ("不必", "无需", "不用", "无须", "不再", "不要求", "不需要", "无需再")
_COMPARE_WORDS = ("比较", "比对", "核对", "校验", "对照")
_AGREEMENT_WORDS = ("一致", "同一", "相同")
_FINGERPRINT_WORDS = ("指纹", "fingerprint")
_SKIP_COMPARISON = re.compile(r"(?:无需|不必|不用|无须|不再|不要求|不需要)")
# A dropped repeat or extra comparison keeps the binding intact, whether the
# qualifier is written before or after the cancellation word.
_SKIP_EXEMPT = re.compile(r"(?:重复|再次|重新|额外|另行|二次)")
_MISMATCH_STOP = re.compile(
    r"(?:不一致|不符合|不同)[^。；\n]{0,12}(?:立即)?(?:停止|结束|error|失败)")

STEP1_NAME = "Step 1 — Resolve program root + runner plan"
STEP3_NAME = "Step 3 — 跑 stage3-finalize（校验 + 状态写入 + 确定性渲染）"


def _agent_steps(agent):
    """Return the `### Step n` sections of the agent document, keyed by title."""
    starts = list(re.finditer(r"(?m)^### (Step [^\n]+)$", agent))
    return {match.group(1).strip():
            agent[match.start():starts[index + 1].start()
                  if index + 1 < len(starts) else len(agent)]
            for index, match in enumerate(starts)}


def _binding_branches(step3):
    """Split the finalize-side binding rule into its two profile branches.

    The branches are read from the binding paragraph alone, so the runner
    bullets that follow it can never be mistaken for the no-profile branch.
    The paragraph may be re-flowed across lines: a line break inside the rule
    keeps the same contract and must not be read as a missing branch.  A
    document whose profile-present branch condition is missing yields no
    branches at all, which is what the frozen rule forbids.
    """
    parts = _STEP3_START.split(step3, 1)
    body = parts[1] if len(parts) > 1 else step3
    stop = _BIND_PARAGRAPH_END.search(body)
    if stop:
        body = body[:stop.start()]
    separator = body.find("\n\n")
    if separator >= 0:
        body = body[:separator]
    body = body.replace("\n", "")
    with_profile = _BRANCH_WITH_PROFILE.search(body)
    no_profile = _BRANCH_NO_PROFILE.search(body)
    if not with_profile or not no_profile or no_profile.start() < with_profile.start():
        return None, None
    return (body[with_profile.start():no_profile.start()],
            body[no_profile.start():])


def _binding_clauses(text):
    """Split one binding branch into punctuation-separated clauses."""
    return [clause.strip() for clause in _CLAUSE_SPLIT.split(text) if clause.strip()]


def _fingerprint_source_clause(clauses):
    """Return the clause that pins where the committed fingerprint is read from."""
    for index, clause in enumerate(clauses):
        if not _BIND_FIELD.search(clause):
            continue
        window = "，".join(clauses[max(0, index - 2):index + 1])
        if _STATE_SOURCE.search(window) \
                or any(ref in window for ref in _CLOSE_REFS):
            return clause
    return None


def _response_is_fingerprint_source(clauses):
    """True when a clause reads profile_fingerprint out of the finalize response.

    This is the edc39f6 defect: the value has to come from the committed state
    file named by the returned state_path, never from the finalize response.
    """
    for clause in clauses:
        if not _BIND_FIELD.search(clause):
            continue
        if _RESPONSE_FIELD_SOURCE.search(clause):
            return True
    return False


def _clause_skips_comparison(sentence):
    """True when one clause drops the comparison instead of a repeat of it.

    A cancellation only reads as harmless when the same comma-separated clause
    still requires the comparison ("need not compare again because the check
    after finalize must match"); a requirement stated in a later clause cannot
    rescue an earlier clause that drops the comparison outright.
    """
    if not (_CONCORDANCE_SENTENCE.search(sentence)
            or _COMPARISON_TOPIC.search(sentence)):
        return False
    chunks = _CANCEL_CLAUSE_SPLIT.split(sentence)
    for chunk in chunks:
        matches = list(_SKIP_COMPARISON.finditer(chunk))
        if not matches:
            continue
        # A requirement inside the same comma-separated clause keeps the
        # binding ("need not compare again because the check must match"); a
        # requirement in a later clause cannot rescue an earlier clause that
        # drops the comparison outright.
        if _COMPARISON_REQUIRED.search(chunk):
            continue
        for match in matches:
            tail = chunk[match.end():]
            if _SKIP_EXEMPT.search(chunk[max(0, match.start() - 6):match.start()] + tail):
                continue
            if any(word in tail for word in _COMPARE_WORDS + _AGREEMENT_WORDS):
                return True
    return False


def _concordance_cancelled(text):
    """True when the text cancels the plan/committed fingerprint comparison.

    The cancellation has to sit in the same sub-clause as the agreement or
    comparison wording, which covers "but it need not match the plan
    fingerprint" and "but the run need not compare the two fingerprints".  A
    dropped repeat ("need not compare again, the check after finalize still has
    to match") keeps the binding and is not a cancellation.
    """
    return any(_clause_skips_comparison(sentence)
               for sentence in _CLAUSE_SPLIT.split(text))


def _skips_comparison(text):
    """True when a sentence demands skipping the fingerprint comparison.

    A sentence that negates the comparison itself ("this round need not compare
    the committed fingerprint with the plan fingerprint") contradicts the
    binding rule wherever it sits in the profile branch, including in front of
    the parts that carry the binding markers.  The whole sub-clause is read, so
    a cancellation written as "need not carry out a comparison of ..." is still
    caught.
    """
    return any(_clause_skips_comparison(sentence)
               for sentence in _CLAUSE_SPLIT.split(text))


def _doc_binding_disposition(agent):
    """Decide whether the agent document carries the frozen binding contract.

    Judged over the two branches of the finalize-side rule plus the plan-side
    hard check: (1) the branch condition on this round's profile, (2) the
    fingerprint read from committed state and not from the finalize response,
    (3) the plan/path/fingerprint consistency demands — non-empty, matching the
    plan fingerprint, and stopping on a mismatch or an unreadable state — with
    the plan-side stop before any candidate result file is written, and (4) the
    explicit null-is-legal continuation when no profile exists.
    """
    if not _STEP3_START.search(agent):
        return False, "missing finalize-side binding rule"
    steps = _agent_steps(agent)
    step1, step3 = steps.get(STEP1_NAME), steps.get(STEP3_NAME)
    if step1 is None or step3 is None:
        return False, "missing Step 1 / Step 3 section"
    with_profile, no_profile = _binding_branches(step3)
    if with_profile is None:
        return False, "binding rule states no profile-present / no-profile branches"

    profile_clauses = _binding_clauses(with_profile)
    if _response_is_fingerprint_source(profile_clauses):
        return False, "fingerprint read from the finalize response"
    if _fingerprint_source_clause(profile_clauses) is None:
        return False, "fingerprint source (state_path / state file) not pinned"
    for clause in profile_clauses:
        if _UNCONDITIONAL.search(clause) and (_MUST_NONEMPTY.search(clause)
                                              or _STOP_VERB.search(clause)):
            return False, "unconditional non-empty/stop demand in the profile branch"
    body_clauses = None
    for index, clause in enumerate(profile_clauses):
        if _BIND_FAIL_MARKER in clause or _UNCONDITIONAL.search(clause):
            body_clauses = profile_clauses[index:]
            break
    force_scope = "，".join(body_clauses or profile_clauses)
    if not _PROFILE_SCOPE.search(force_scope):
        return False, "empty-fingerprint failure not scoped to this round's profile"
    if not _READ_FAIL_STOP.search(force_scope):
        return False, "unreadable committed state not stopped on"
    if not _MISMATCH_STOP.search(force_scope):
        return False, "plan/committed fingerprint mismatch not stopped on"
    if not _CONCORDANCE_SENTENCE.search(force_scope):
        return False, "committed fingerprint not required to match the plan fingerprint"
    # The cancellation checks cover the whole profile-present branch: a
    # cancelling sentence placed in front of the marker-carrying parts would
    # otherwise be cut away from the checked scope.
    if _concordance_cancelled(with_profile) or _skips_comparison(with_profile):
        return False, "plan/committed fingerprint comparison cancelled in the profile branch"
    if _BIND_FAIL_MARKER not in force_scope:
        return False, "missing profile_fingerprint_binding_failed note"

    no_clauses = _binding_clauses(no_profile)
    if any(_NO_PROFILE_STOP_WORD.search(clause)
           or _UNCONDITIONAL.search(clause) and _STOP_VERB.search(clause)
           for clause in no_clauses):
        return False, "no-profile branch demands a stop"
    null_clause = next((clause for clause in no_clauses
                        if _NULL_IS_LEGAL.search(clause)), None)
    if null_clause is None:
        return False, "no-profile null fingerprint not declared a legal result"
    if _NULL_DEMAND.search(null_clause):
        return False, "no-profile branch demands a non-empty fingerprint"
    if not any(_NULL_VALUE.search(clause) and _ALLOW_CONTINUE.search(clause)
               for clause in no_clauses):
        return False, "no-profile null fingerprint not declared legal to continue"

    plan_clauses = [chunk.strip()
                    for chunk in re.split(r"(?m)^\d+\.\s+|\n", step1)
                    if chunk.strip()]
    plan_index = next((index for index, chunk in enumerate(plan_clauses)
                       if "指纹硬检查" in chunk), None)
    if plan_index is None:
        return False, "missing plan-side hard fingerprint check"
    plan_clause = plan_clauses[plan_index]
    # The section intro can ride along on the same split chunk; the check
    # itself starts at its own label.
    plan_check = plan_clause[plan_clause.index("**plan 指纹硬检查**"):]
    if _BIND_FAIL_MARKER not in plan_check:
        return False, "plan-side check missing profile_fingerprint_binding_failed"
    if not _PROFILE_SCOPE.search(plan_check):
        return False, "plan-side check not scoped to this round's profile"
    if not _MUST_NONEMPTY.search(plan_check):
        return False, "plan-side check missing the non-empty fingerprint demand"
    # The plan-side stop point is pinned by the fail-closed rationale of the
    # finalize-side rule (the plan check itself defers to Step 1.5 for it).
    if not _EARLY_STOP_BEFORE_WRITE.search(with_profile):
        return False, "plan-side stop not pinned before the result files are written"
    return True, "conditional branch committed-state source and both stop points"


# -- S3-DOC-1 binding fact table (issue-66 gate2 revision, 2026-10-04 20:02) --
#
# The 2026-10-04 20:02 review asks for the frozen facts of plan r11 §4 to be
# proved one by one instead of patching a regex per counterexample.  Each fact
# below has a judgment and at least one minimal mutation that changes only that
# fact, plus a legal control where the wording must stay free.

_BINDING_HEADING = re.compile(r"\*\*finalize 指纹绑定检查（")
_PLAN_CHECK_LABEL = "**plan 指纹硬检查**"
_REBIND_PLAN_FINALIZE = re.compile(
    r"stage3-plan[^。；\n]{0,60}stage3-finalize|"
    r"stage3-finalize[^。；\n]{0,60}stage3-plan")
_REBIND_NAMES = ("stage3-plan", "stage3-finalize")
_TUPLE_NAMES = ("source tuple", "professor_dir", "program_root", "refresh_scope",
                "skip_direction_ids", "cross_direction_groups", "validation_file")
_TUPLE_PIN = re.compile(r"固定\s*source\s*tuple|同一\s*tuple|同一\s*source\s*tuple")
_TUPLE_CORRECTION = re.compile(
    r"修正轮[^。；\n]{0,24}(?:只|仅)[^。；\n]{0,8}(?:增加|加入|新增)|"
    r"只增加[^。；\n]{0,12}validation_file")
_SAME_PROFILE_PATH = re.compile(
    r"(?:逐字复用|沿用|重复使用)[^。；\n]{0,40}(?:绝对路径|路径字符串)|"
    r"(?:绝对路径|路径字符串)[^。；\n]{0,30}(?:逐字复用|沿用|完全相同)")
_UNCHANGED_PROFILE_PATH = re.compile(r"绝不[^。；\n]{0,8}(?:重新解析|临场替换)")
_PLAN_BIND_RESOLVED = re.compile(
    r"绑定\s*本\s*child[^。；\n]{0,12}(?:传入|解析)[^。；\n]{0,12}(?:同一\s*)?"
    r"`?--profile`?|绑定\s*(?:已解析|resolved)[^。；\n]{0,12}profile")
_COMMITTED_NONEMPTY = re.compile(
    r"提交[^。；\n]{0,24}非空|非空[^。；\n]{0,24}提交|"
    r"必须是非空(?:字符串)?|`profile_fingerprint`[^。；\n]{0,20}必须是非空")
_NULLISH = ("null", "`null`", "空指纹", "为空")
_NULL_STOP = re.compile(
    r"得到[^。；\n]{0,12}`?null`?[^。；\n]{0,30}?(?:停止|结束|失败)|"
    r"空指纹[^。；\n]{0,16}(?:立即)?(?:停止|结束|失败)")
_FORBIDDEN_ACTIONS = ("不进入 Step 3.6", "不运行 `stage3-record-validation`", "不重建总览")
_NO_OK_RETURN = re.compile(r"绝不返回\s*`?ok`?")
_NO_PROFILE_ERROR = re.compile(
    r"(?:null|`null`|空指纹)[^。；\n]{0,8}(?:时|则)?[^。；\n]{0,8}返回\s*error")
_NO_PROFILE_CONTINUE = re.compile(r"不报错|合法结果")
_FIELD_READ = re.compile(
    r"(?:读取|读|取|核对)[^。；\n]{0,30}`?profile_fingerprint`?|"
    r"`?profile_fingerprint`?[^。；\n]{0,16}(?:必须|一致)")
_OTHER_SOURCE = re.compile(
    r"(?:临时|缓存|内存|环境变量|响应)[^。；\n]{0,12}(?:读取|中的)|"
    r"从[^。；\n]{0,8}响应[^。；\n]{0,8}(?:读取|取)")
_BIND_PARAGRAPH_END = re.compile(r"(?m)^- |^### |^\*\*")
_COMPARISON_REQUIRED = re.compile(
    r"(?:必须|应当|应|要)[^。；\n]{0,24}(?:比较|比对|核对|一致|相同|同一)|"
    r"(?:一致|相同|同一)[^。；\n]{0,12}(?:必须|否则|不通过)")
_MUTATION_BIND_FAIL = "必填项不满足时照样继续处理，并记录警告"
_PLAN_SCOPE_PHRASE = "存在 profile 时"
_PLAN_NONEMPTY_PHRASE = "必须是非空字符串且绑定本 child 传入的同一 `--profile`"
_PLAN_BIND_PHRASE = "绑定本 child 传入的同一 `--profile`"


def _binding_paragraph(agent):
    """Return the whole finalize-side binding paragraph, across line breaks."""
    match = _BINDING_HEADING.search(agent)
    if not match:
        return None
    end = len(agent)
    for stop in (_BIND_PARAGRAPH_END.search(agent, match.end()),
                 agent.find("\n\n", match.end()) if agent.find("\n\n", match.end()) >= 0
                 else None):
        if stop is not None:
            end = min(end, stop.start() if hasattr(stop, "start") else stop)
    return agent[match.start():end]


def _revised_span(step1, step3, whole, old, new, label):
    """Replace one span in whichever section holds it, keeping the rest as is."""
    if old in step3:
        return whole.replace(step3, step3.replace(old, new, 1), 1)
    if old in step1:
        return whole.replace(step1, step1.replace(old, new, 1), 1)
    raise AssertionError(f"{label}: span not found :: {old[:60]}")


def _binding_facts(agent, skill):
    """Prove the plan r11 §4 source-binding facts one by one.

    Returns a list of (fact_id, ok, reason).  The facts are judged on the
    agent's own contract text, with the Skill's Stage 3 boundary as the
    cross-check for the same input group.
    """
    facts = []
    paragraph = _binding_paragraph(agent)
    if paragraph is None:
        return [("F4.0", False, "binding paragraph not found")]

    reuses = (any(name in paragraph for name in _REBIND_NAMES)
              and bool(_SAME_PROFILE_PATH.search(paragraph)))
    # A correction round reuses the same source tuple and only adds the
    # validation file that the previous round recorded.
    correction_keeps = re.search(
        r"修正轮[^。；\n]{0,60}(?:同一|相同)[^。；\n]{0,16}validation"
        r"|(?:stage3-plan|plan)[^。；\n]{0,12}(?:与|和|/)[^。；\n]{0,12}finalize"
        r"[^。；\n]{0,30}(?:同一|相同)[^。；\n]{0,12}validation", agent)
    facts.append(("F4.1",
                  bool(reuses) and bool(correction_keeps),
                  "plan/finalize must reuse one source tuple, and a correction "
                  "round only adds the recorded validation file"))
    facts.append(("F4.2a", bool(_SAME_PROFILE_PATH.search(paragraph))
                  and bool(_UNCHANGED_PROFILE_PATH.search(paragraph)),
                  "both commands must use the same absolute --profile path"))
    present_branch, _no_profile = _binding_branches(agent)
    if present_branch is None:
        present_branch = paragraph
    facts.append(("F4.2b",
                  bool(re.search(r"(?:同一|相同)\s*`--profile`", present_branch))
                  and bool(re.search(r"stage3-plan[^。；\n]{0,24}(?:同一|相同)", present_branch))
                  and bool(re.search(r"本命令的\s*`--profile`", present_branch)),
                  "both commands must carry the same --profile argument"))
    plan_clause = re.search(r"\*\*plan 指纹硬检查\*\*[^\n]*", agent)
    plan_clause = plan_clause.group() if plan_clause else present_branch
    facts.append(("F4.3", bool(_PLAN_BIND_RESOLVED.search(plan_clause)),
                  "the plan fingerprint must bind the resolved profile"))
    facts.append(("F4.4", bool(_COMMITTED_NONEMPTY.search(paragraph)),
                  "the committed fingerprint must be non-empty"))
    nullish = [name for name in _NULLISH if name in paragraph]
    facts.append(("F4.5",
                  bool(_NULL_STOP.search(paragraph)) and bool(nullish),
                  "a null committed fingerprint must stop the child"))
    facts.append(("F4.6",
                  all(action in paragraph for action in _FORBIDDEN_ACTIONS)
                  and bool(_NO_OK_RETURN.search(paragraph)),
                  "binding failure must forbid the later stage 3 actions"))
    facts.append(("F4.7",
                  bool(_NO_PROFILE_CONTINUE.search(paragraph))
                  and not _NO_PROFILE_ERROR.search(paragraph),
                  "a no-profile round must not return an error"))
    source_clause = _fingerprint_source_clause(_binding_clauses(paragraph))
    if source_clause is None:
        facts.append(("F4.8", False, "committed-state source clause not found"))
    else:
        facts.append(("F4.8",
                      bool(_STATE_SOURCE.search(source_clause))
                      and bool(_FIELD_READ.search(source_clause))
                      and not _OTHER_SOURCE.search(source_clause),
                      "the value must be read from the named state file"))

    section = _stage34_section(skill)
    facts.append(("F4.9",
                  bool(_TUPLE_PIN.search(section))
                  and bool(_TUPLE_CORRECTION.search(section)),
                  "the skill boundary must pin one tuple, adding only "
                  "validation_file for a correction round"))
    return facts


def _stage34_section(skill):
    """Return the Stage 3/4 orchestration boundary section of the Skill."""
    start = skill.find("### Stage 3/4 编排边界")
    if start < 0:
        return ""
    end = skill.find("\n### ", start + 1)
    return skill[start:end if end > 0 else len(skill)]


def _codex_bullet(skill):
    """Return the Codex sibling-orchestration bullet of the Skill boundary."""
    section = _stage34_section(skill)
    start = section.find("- **Codex（root caller")
    if start < 0:
        return ""
    end = section.find("\n- **", start + 1)
    return section[start:end if end > 0 else len(section)]


def _source_binding_mutation_cases(agent, skill):
    """Mutations that each break exactly one source-binding fact."""
    paragraph = _binding_paragraph(agent)
    steps = _agent_steps(agent)
    step1 = steps.get(STEP1_NAME, "")
    step3 = steps.get(STEP3_NAME, "")
    plan_line = next((line for line in agent.splitlines()
                      if _PLAN_CHECK_LABEL in line), "")
    section = _stage34_section(skill)
    cases = []

    def case(fact_id, label, mutated):
        cases.append((fact_id, label, mutated))


    same_path = _SAME_PROFILE_PATH.search(paragraph)
    if same_path:
        mutated = agent.replace(same_path.group(), "单独解析 profile", 1)
        case("F4.2a", "profile path re-resolved", mutated)
    plan_arg = re.search(r"`stage3-plan`[^。；\n]{0,8}与本命令都传了[^。；\n]{0,8}`--profile`",
                         paragraph)
    if plan_arg:
        case("F4.2b", "plan no longer carries the same --profile",
             agent.replace(plan_arg.group(), "`stage3-plan` 单独解析自己的 profile"))
    plan_binding = re.search(r"且?绑定本 child 传入的同一 `--profile`", plan_line)
    if plan_binding:
        case("F4.3", "plan binding loses the resolved profile",
             agent.replace(plan_line,
                           plan_line.replace(plan_binding.group(),
                                             "非空即可，无需对应已解析 profile"), 1))
    if _COMMITTED_NONEMPTY.search(paragraph):
        match = _COMMITTED_NONEMPTY.search(paragraph)
        case("F4.4", "committed fingerprint may be empty",
             agent.replace(match.group(), "可以为空在任何情况下"))
    null_line = _NULL_STOP.search(paragraph)
    if null_line:
        case("F4.5", "null no longer stops the child",
             agent.replace(null_line.group(), "为空时继续按既有无资料行为处理"))
    case("F4.6", "later stage 3 actions stay allowed",
         agent.replace("不进入 Step 3.6 validator 循环", "进入 Step 3.6 validator 循环"))
    no_profile = _BRANCH_NO_PROFILE.search(paragraph)
    if no_profile:
        case("F4.7", "no-profile null returns an error",
             agent.replace(paragraph,
                           paragraph.replace("是合法结果", "时返回 error 并停止", 1), 1))
    source_clause = _fingerprint_source_clause(_binding_clauses(paragraph))
    if source_clause:
        case("F4.8", "value read from a temporary cache",
             agent.replace(source_clause,
                           source_clause.replace("该状态文件里实际提交的", "本地临时缓存中的", 1), 1))
    if reuses_text := re.search(r"此后的[^。；\n]{0,40}", paragraph):
        case("F4.1", "no shared source tuple",
             agent.replace(reuses_text.group(), "此后两步各按当次解析结果执行。"))
    if "只增加" in section:
        case("F4.9", "correction round may change the source",
             skill.replace("只增加", "可以更换", 1))
    return cases


# -- S3-DOC-1 state machine / raw handoff / rebuild fact table ---------------

_PAT_G1_STOP = re.compile(r"G1`?\s*非成功[^。；\n]{0,24}立即停止 Stage 3")
_PAT_G1_NO_V1 = re.compile(r"不派发\s*V1|不得派发\s*V1")
_PAT_RECORD_V1_PASS = re.compile(
    r"needs_correction=false[^。；\n]{0,24}(?:立即\s*terminal|终局)")
_PAT_G2_STOP = re.compile(r"G2`?\s*非成功[^。；\n]{0,40}立即停止 Stage 3")
_PAT_G2_NO_V2 = re.compile(r"不派发\s*V2|禁止\s*V2|不得派发\s*V2")
_PAT_NO_RETRY = re.compile(r"不得\s*retry\s*generator|不得再派发任何新 generator")
_PAT_V2_RECORD = re.compile(r"V2[^。；\n]{0,24}record[^。；\n]{0,24}terminal")
_PAT_NO_THIRD = re.compile(r"禁止再委派 idea-generator|不存在第\s*3\s*个\s*generator"
                           r"|不再委派 idea-generator")
_PAT_CHILD_COUNT = re.compile(r"child[^。；\n]{0,12}只能\s*(?:是)?\s*2\s*(?:或|/)\s*4")
_PAT_FIFTH = re.compile(
    r"第\s*5\s*个[^。；\n，]{0,10}(?:caller contract violation|contract violation|非法|violation)")
_PAT_NO_INLINE = re.compile(r"不得\s*inline")
_PAT_INLINE_TARGETS = re.compile(r"stage3-plan|stage3-finalize")
_PAT_UNIQUE_MESSAGE = re.compile(r"唯一最终业务")
_PAT_BYTE_EXACT = re.compile(r"逐字节相同|逐字节比对")
_PAT_NO_TRAILING_NEWLINE = re.compile(r"不得新增结尾换行|不新增结尾换行")
_PAT_SAME_FILE = re.compile(r"同一个文件|同一文件|同一份文件")
_PAT_RECORD_CMD = re.compile(r"stage3-record-validation")
_PAT_RECORD_HANDOFF = re.compile(
    r"(?:把|将)[^。；\n]{0,30}(?:原始 JSON|原始业务 JSON|该轮原始 JSON)"
    r"[^。；\n]{0,30}交给\s*`stage3-record-validation`")
_PAT_RECORD_THEN_PLAN = re.compile(
    r"stage3-record-validation[^。；\n]{0,30}在[^。；\n]{0,20}"
    r"stage3-plan\s*--validation-file[^。；\n]{0,10}之前")
_PAT_AFTER_TERMINAL = re.compile(r"terminal[^。；\n]{0,24}之后")
_PAT_ONCE = re.compile(r"恰好一次|一次")
_PAT_BEST_EFFORT = re.compile(r"best-effort")
_PAT_REBUILD_CMD = re.compile(r"stage3-rebuild-overview")
_PAT_NO_REVERSE = re.compile(
    r"(?:不反转|绝不反转)[^。；\n]{0,12}local terminal|"
    r"绝不把已\s*terminal[^。；\n]{0,16}改回|不把已\s*terminal[^。；\n]{0,16}改回")
_PAT_NO_REFINALIZE = re.compile(r"不为修(?:总览|overview)重跑\s*finalize")
_PAT_OVERVIEW_NOT_PROOF = re.compile(
    r"(?:overview_md|overview)[^。；\n]{0,30}不是[^。；\n]{0,16}成功证据")
_PAT_ROOT_REPORTS = re.compile(r"在\s*root[^。；\n]{0,24}报告|root[^。；\n]{0,10}汇报")
_PAT_NO_EDIT_RETURN = re.compile(r"不得事后修改它|不得事后改\s*idea-generator")
_PAT_IDEAGEN_REBUILD_AFTER = re.compile(r"由你在终局记录后运行|终局记录之后由你")
_PAT_CODEX_REBUILD_AFTER = re.compile(r"Codex 下 rebuild 由调用线程在你返回之后")


def _facts_from_table(table, text):
    """Judge one fact table against one document, returning fact rows."""
    rows = []
    for fact_id, predicate, reason in table:
        try:
            rows.append((fact_id, bool(predicate(text)), reason))
        except Exception as exc:  # a malformed pattern is a failed fact
            rows.append((fact_id, False, f"{reason} :: {type(exc).__name__}"))
    return rows


def _state_machine_block(skill):
    """Return the hard stop-point paragraph of the Skill state machine."""
    section = _stage34_section(skill)
    start = section.find("停止点是硬边界")
    if start < 0:
        return ""
    end = section.find("\n- **", start + 1)
    return section[start:end if end > 0 else len(section)]


_BOUNDARY_TABLE = [
    ("F5.8", lambda t: _PAT_RECORD_HANDOFF.search(t),
     "the boundary hands the round JSON to the record command"),
    ("F5.9", lambda t: _PAT_NO_INLINE.search(t),
     "the boundary forbids inlining the named agents"),
]

_STATE_MACHINE_TABLE = [
    ("F5.1", lambda t: _PAT_G1_STOP.search(t) and _PAT_G1_NO_V1.search(t),
     "a failed G1 must stop before V1"),
    ("F5.3", lambda t: _PAT_G2_STOP.search(t) and _PAT_G2_NO_V2.search(t),
     "a failed G2 must stop before V2"),
    ("F6.1", lambda t: _PAT_BYTE_EXACT.search(t),
     "the raw validator message is written byte-exact"),
]

_SKILL_BULLET_TABLE = [
    ("F5.2", lambda t: _PAT_RECORD_V1_PASS.search(t),
     "record(V1) without correction must be terminal"),
    ("F5.4", lambda t: _PAT_NO_RETRY.search(t),
     "a stopped round must not retry the generator"),
    ("F5.5", lambda t: _PAT_V2_RECORD.search(t) and _PAT_NO_THIRD.search(t),
     "V2 is recorded once and no third generator follows"),
    ("F5.6", lambda t: _PAT_CHILD_COUNT.search(t) and _PAT_FIFTH.search(t),
     "the root keeps 2 or 4 stage-3 children"),
    ("F6.2", lambda t: _PAT_SAME_FILE.search(t) and _PAT_RECORD_CMD.search(t),
     "the same file is handed to the record command"),
    ("F7.1", lambda t: _PAT_REBUILD_CMD.search(t) and _PAT_AFTER_TERMINAL.search(t)
     and _PAT_ONCE.search(t) and _PAT_BEST_EFFORT.search(t),
     "the rebuild runs once, after the terminal record, best-effort"),
    ("F7.2", lambda t: _PAT_NO_REVERSE.search(t) and _PAT_NO_REFINALIZE.search(t),
     "a rebuild failure must not reverse the terminal or rerun finalize"),
    ("F7.3", lambda t: _PAT_OVERVIEW_NOT_PROOF.search(t),
     "the overview path is not success evidence"),
    ("F7.4", lambda t: _PAT_ROOT_REPORTS.search(t) and _PAT_NO_EDIT_RETURN.search(t),
     "the Codex root reports the rebuild result and cannot edit the return"),
]

_AGENT_TABLE = [
    ("F7.5", lambda t: _PAT_IDEAGEN_REBUILD_AFTER.search(t),
     "the OpenCode owner runs the rebuild after the terminal record"),
    ("F7.6", lambda t: _PAT_CODEX_REBUILD_AFTER.search(t),
     "the Codex root owns the rebuild after the child returned"),
    ("F7.7", lambda t: _PAT_OVERVIEW_NOT_PROOF.search(t),
     "the agent document states the overview path is not success evidence"),
]

_WFREF_TABLE = [
    ("F7.8", lambda t: _PAT_UNIQUE_MESSAGE.search(t) and _PAT_BYTE_EXACT.search(t)
     and bool(_PAT_NO_TRAILING_NEWLINE.search(t)),
     "the reference freezes the byte-exact raw handoff"),
    ("F7.9", lambda t: _PAT_CHILD_COUNT.search(t) and _PAT_FIFTH.search(t),
     "the reference freezes the 2 or 4 sibling bound"),
]


def _state_machine_facts(agent, skill, wfref):
    """Prove the Codex state machine, raw handoff and rebuild contract facts."""
    table = [
        ("F6.3", lambda t: _PAT_RECORD_THEN_PLAN.search(t),
         "the record must happen before the correction plan uses the file"),
    ]
    facts = _facts_from_table(_STATE_MACHINE_TABLE, _state_machine_block(skill))
    facts += _facts_from_table(_BOUNDARY_TABLE, _stage34_section(skill))
    facts += _facts_from_table(_SKILL_BULLET_TABLE, _codex_bullet(skill))
    facts += _facts_from_table(table, _stage34_section(skill))
    facts += _facts_from_table(_AGENT_TABLE, agent)
    facts += _facts_from_table(_WFREF_TABLE, wfref)
    return facts


def _state_machine_mutation_cases(agent, skill, wfref):
    """Mutations that each break exactly one state machine / handoff fact.

    Each row is (fact_id, target document, label, mutated document).
    """
    block = _state_machine_block(skill)
    bullet = _codex_bullet(skill)
    section = _stage34_section(skill)

    def swap(source, old, new, label):
        if old not in source:
            raise AssertionError(f"{label}: span not found :: {old[:50]}")
        return source.replace(old, new, 1)

    return [
        ("F5.1", "skill", "a failed G1 still dispatches V1",
         swap(block, "不派发 V1", "仍然派发 V1 继续尝试", "F5.1")),
        ("F5.2", "skill", "a passing record still dispatches G2",
         swap(bullet, "不得再委派 idea-generator",
              "仍需继续委派 idea-generator 再生成一轮", "F5.2")),
        ("F5.3", "skill", "a failed G2 still dispatches V2",
         swap(block, "不派发 V2", "可以派发 V2 再校验一次", "F5.3")),
        ("F5.4", "skill", "a stopped round retries the generator",
         swap(bullet, "不得 retry generator", "可以 retry generator", "F5.4")),
        ("F5.5", "skill", "a third generator follows V2",
         swap(bullet, "不存在第 3 个 generator",
              "第 3 个 generator 可以按需要继续派发", "F5.5")),
        ("F5.6", "skill", "the fifth child is allowed",
         swap(swap(section, "第 5 个 child 一律是 caller contract violation",
                   "第 5 个 child 属于允许的补充校验，不是 caller contract violation",
                   "F5.6/section"),
              "第 5 个即 caller contract violation",
              "第 5 个属于允许的补充校验，不算 caller contract violation", "F5.6/bullet")),
        ("F5.9", "skill", "the caller may inline the named agents",
         swap(swap(section, "不得 inline", "可以 inline", "F5.9/section"),
              "不得 inline", "可以 inline", "F5.9/bullet")),
        ("F6.1", "skill", "the handoff is re-serialized",
         swap(block, "逐字节相同", "字段等价即可", "F6.1")),
        ("F6.2", "skill", "record-validation consumes a rewritten copy",
         swap(bullet, "同一文件", "改写后的副本", "F6.2")),
        ("F6.3", "skill", "the order dependency is reversed",
         swap(section, "`stage3-record-validation` 必须在 `stage3-plan --validation-file` 之前完成",
              "`stage3-plan --validation-file` 必须在 `stage3-record-validation` 之前完成",
              "F6.3")),
        ("F7.1", "skill", "the rebuild runs twice around the terminal",
         swap(bullet, "best-effort 运行一次",
              "terminal 之前先 rebuild 一次、terminal 之后再 rebuild 一次", "F7.1")),
        ("F7.2", "skill", "a rebuild failure reruns finalize",
         swap(bullet, "不为修总览重跑 finalize",
              "总览失败时可以重跑 finalize 修好它", "F7.2")),
        ("F7.3", "skill", "the overview path becomes success evidence",
         swap(bullet, "不是成功证据", "可以作为成功证据", "F7.3")),
        ("F7.4", "skill", "the root edits the child return",
         swap(bullet, "不得事后修改它", "可以事后修正它", "F7.4")),
        ("F7.5", "agent", "the OpenCode owner rebuilds before the record",
         swap(agent, "由你在终局记录后运行",
              "由你在终局记录之前运行", "F7.5")),
        ("F7.6", "agent", "the agent claims the Codex rebuild itself",
         swap(agent, "Codex 下 rebuild 由调用线程在你返回之后自己运行",
              "Codex 下 rebuild 同样由你自己运行", "F7.6")),
        ("F7.7", "agent", "the agent calls the overview a success proof",
         swap(agent, "永远不是 rebuild 成功证据",
              "就是 rebuild 成功证据", "F7.7")),
        ("F7.8", "wfref", "the reference loses the byte-exact handoff",
         swap(wfref, "不得新增结尾换行", "可以补一个结尾换行", "F7.8")),
        ("F7.9", "wfref", "the reference loosens the sibling bound",
         swap(wfref, "第 5 个即 caller contract violation",
              "第 5 个属于允许的补充校验，不算 caller contract violation", "F7.9")),
        ("F5.8", "skill", "the round JSON bypasses the record command",
         swap(section, "把该轮原始 JSON 交给 `stage3-record-validation`",
              "把该轮原始 JSON 直接交给修正代理，跳过记录命令", "F5.8")),
    ]


class TestIssue66Stage3(Stage3DirectionGroupBase):
    """One professor A (dir_A/dir_B + shared paper) from the shared builder."""

    def setUp(self):
        super().setUp()
        self.overview_path = self.root / "教授研究" / CANDIDATES_OVERVIEW
        self.registry_path = self.root / "教授研究" / PROJECTIONS_FILE

    # -- shared helpers ---------------------------------------------------

    def write_a_results(self, name, docs=None):
        docs = docs or {"dir_A": self.generated_doc("dir_A", ["P1", "P2", None]),
                        "dir_B": self.generated_doc("dir_B", ["P1", "P3", None])}
        return self.write_results(name, docs)

    def write_a_cross(self, results):
        """Write professor A's explicit cross-direction group result."""
        write_json(results / result_file("candidates", CROSS_GID),
                   {"schema": 2, "kind": "cross_candidates",
                    "group_id": CROSS_GID, "direction_ids": ["dir_A", "dir_B"],
                    "candidates": [self.cross_candidate(
                        "XA", ["dir_A", "dir_B"], ["P2", "P3"], ["P1"],
                        gap_owner={"P2": "dir_A", "P3": "dir_B"})]})
        return results

    def finalize_a_ok(self, name="s3-a", *extra):
        results = self.write_a_results(name)
        out = self.stage3_finalize(results, *extra)
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    def snapshot(self, *paths):
        return {Path(p): (Path(p).read_bytes() if Path(p).exists() else None)
                for p in paths}

    def assert_unchanged(self, before):
        for path, old in before.items():
            current = path.read_bytes() if path.exists() else None
            self.assertEqual(current, old, f"unexpected change: {path}")

    def overview_business_body(self):
        """Overview body minus the volatile generation-timestamp line."""
        _, body = contact_state.split_frontmatter(
            self.overview_path.read_text(encoding="utf-8"))
        return "\n".join(line for line in body.splitlines()
                         if not line.startswith("> 2"))

    def build_twin_professor(self):
        """Second professor with the SAME display name, direction IDs and
        cross-group ID as professor A, in a different canonical directory."""
        self.twin_gap_ids = {key: quote_id(quote)
                             for key, quote in TWIN_QUOTES.items()}
        saved_dir, saved_professor = self.prof_dir, self.professor
        twin_dir = self.root / "教授研究" / "Y分野" / PROFESSOR
        (twin_dir / "论文分析").mkdir(parents=True)
        self.prof_dir, self.professor = twin_dir, PROFESSOR
        try:
            papers = [
                self.make_paper("T1", "Twin Shared Method Paper",
                                ["twin", "shared"], [TWIN_QUOTES["T1"]]),
                self.make_paper("T2", "Twin Signal Paper",
                                ["twin", "signal"], [TWIN_QUOTES["T2"]]),
                self.make_paper("T3", "Twin Sensor Paper",
                                ["twin", "sensor"], [TWIN_QUOTES["T3"]]),
            ]
            directions = [
                self.make_direction("dir_A", ["T1", "T2"], name_ja="信号処理",
                                    name_zh="信号处理", summary="Twin 信号处理"),
                self.make_direction("dir_B", ["T1", "T3"], name_ja="センサ網",
                                    name_zh="传感网络", summary="Twin 传感网络"),
            ]
            facts_path = self.write_facts(papers, directions, name="facts-twin.json")
            self.run_resolve(facts_path, {})
            payload = self.run_stage2_finalize(facts_path)
            self.assertEqual(payload["status"], "ok",
                             msg=json.dumps(payload, ensure_ascii=False))
        finally:
            self.prof_dir, self.professor = saved_dir, saved_professor
        self.twin_dir = twin_dir
        return twin_dir

    def twin_candidate(self, cid, item_key, direction_id="dir_A"):
        candidate = {"id": cid, "kind": "direction",
                     "direction_ids": [direction_id], "origin": "generated",
                     "title": f"候选 {cid}",
                     "one_liner": "教授的 Twin 工作启发我思考延伸方向",
                     "research_question": "该方法在批量输入下是否保持相同收敛性？",
                     "points": [], "gap_refs": [], "papers": [],
                     "fit": "high", "fit_note": "", "red_lines": [],
                     "why_recommended": "兴趣契合", "tension_points": []}
        if item_key is not None:
            candidate["points"] = ["挂在缺口 1"]
            candidate["gap_refs"] = [{"direction_id": direction_id,
                                      "item_key": item_key,
                                      "gap_id": self.twin_gap_ids[item_key]}]
            candidate["papers"] = [{"item_key": item_key,
                                    "direction_ids": [direction_id],
                                    "role": "基座", "fit_note": "教授通讯"}]
        return candidate

    def twin_doc(self, ckey, item_keys, priority):
        return {"schema": 2, "kind": "candidates", "direction_id": ckey,
                "mode": "generated", "priority": priority,
                "candidates": [self.twin_candidate(f"{ckey}_{n}", key,
                                                   direction_id=ckey)
                               for n, key in enumerate(item_keys, start=1)]}

    def twin_cross_candidate(self, cid):
        idea = self.twin_candidate(cid, None)
        idea["kind"] = "cross_direction"
        idea["direction_ids"] = ["dir_A", "dir_B"]
        idea["gap_refs"] = [
            {"direction_id": "dir_A", "item_key": "T2",
             "gap_id": self.twin_gap_ids["T2"]},
            {"direction_id": "dir_B", "item_key": "T3",
             "gap_id": self.twin_gap_ids["T3"]}]
        idea["papers"] = [{"item_key": "T1", "direction_ids": ["dir_A", "dir_B"],
                           "role": "共同基座", "fit_note": "共享论文"}]
        return idea

    def finalize_twin_ok(self, priority_a, cross_count=1):
        """Finalize the twin: dir_A with 4 candidates, dir_B with 3."""
        results = self.root / "twin-s3results"
        results.mkdir(parents=True, exist_ok=True)
        write_json(results / result_file("candidates", "dir_A"),
                   self.twin_doc("dir_A", ["T1", "T2", "T1", "T2"], priority_a))
        write_json(results / result_file("candidates", "dir_B"),
                   self.twin_doc("dir_B", ["T1", "T3", None], "并推 Twin"))
        cross = [self.twin_cross_candidate(f"XB{n}")
                 for n in range(1, cross_count + 1)]
        write_json(results / result_file("candidates", CROSS_GID),
                   {"schema": 2, "kind": "cross_candidates",
                    "group_id": CROSS_GID, "direction_ids": ["dir_A", "dir_B"],
                    "candidates": cross})
        saved_dir, saved_professor = self.prof_dir, self.professor
        self.prof_dir, self.professor = self.twin_dir, PROFESSOR
        try:
            out = self.stage3_finalize(results, "--cross-direction-groups",
                                       CROSS_GROUP_ARG)
        finally:
            self.prof_dir, self.professor = saved_dir, saved_professor
        self.assertEqual(out["status"], "ok", msg=json.dumps(out, ensure_ascii=False))
        return out

    # -- S3-ISO-1 ---------------------------------------------------------

    def test_s3_iso_1_local_finalize_isolation(self):
        """Each single-variable anomaly leaves A's local commit intact.

        Per the frozen recipe the three sub-scenarios run SEPARATELY, each
        with exactly ONE non-owner disturbance in place; A's finalize must
        succeed, the disturbed object's exact bytes must survive, the other
        non-owner objects must stay absent, and the low-level open record
        must prove finalize never opened any of the three.
        """
        a_pack = self.prof_dir / "套磁候选输入.json"
        a_results = self.write_a_results("s3-iso-1")
        foreign_state = self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / CANDIDATE_STATE

        def reset_single_variable_baseline():
            shutil.rmtree(self.root / "教授研究" / "Y分野", ignore_errors=True)
            self.overview_path.unlink(missing_ok=True)
            self.registry_path.unlink(missing_ok=True)

        for disturbance in ("b_state_malformed", "overview_conflict",
                            "registry_malformed"):
            with self.subTest(scenario=disturbance):
                reset_single_variable_baseline()
                if disturbance == "b_state_malformed":
                    foreign_state.parent.mkdir(parents=True, exist_ok=True)
                    foreign_state.write_text("{ malformed foreign state",
                                             encoding="utf-8")
                    disturbed = foreign_state
                elif disturbance == "overview_conflict":
                    self.overview_path.write_text("手工改过的总览\n", encoding="utf-8")
                    disturbed = self.overview_path
                else:
                    self.registry_path.write_text("{ malformed registry",
                                                  encoding="utf-8")
                    disturbed = self.registry_path
                before = self.snapshot(disturbed)

                with OpenRecorder() as recorder:
                    payload, code = call_runner(
                        "stage3-finalize", "--professor-dir", self.prof_dir,
                        "--results", a_results, "--program-root", self.root)
                self.assertEqual(code, 0)
                self.assertEqual(payload["status"], "ok", payload)
                self.assert_unchanged(before)
                # Single variable: the two undisturbed non-owner objects
                # must remain absent for this run.
                for other in (foreign_state, self.overview_path, self.registry_path):
                    if other != disturbed:
                        self.assertFalse(other.exists(),
                                         f"unexpected non-owner object: {other}")
                # Negative proof: none of the three forbidden paths opened.
                for forbidden in (foreign_state, self.overview_path,
                                  self.registry_path):
                    self.assertFalse(recorder.was_opened(forbidden))
                # Positive control: the recorder sees A's own real reads.
                self.assertTrue(recorder.was_opened(a_pack))

    # -- S3-ISO-3 ---------------------------------------------------------

    def test_s3_iso_3_local_manual_conflict(self):
        """A's own manually edited local Markdown still fails closed."""
        self.finalize_a_ok("s3-iso-3")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        md_path.write_text(
            md_path.read_text(encoding="utf-8") + "\n人工修改的一行\n",
            encoding="utf-8")
        manual_md = md_path.read_bytes()
        before = self.snapshot(state_path, self.overview_path, self.registry_path)

        out = self.stage3_finalize(self.write_a_results("s3-iso-3-reuse"))

        self.assertEqual(out["status"], "needs_decision", out)
        self.assertEqual(out["reason_code"], "manual_markdown_changed")
        self.assert_unchanged(before)
        self.assertEqual(md_path.read_bytes(), manual_md)

    # -- S3-ISO-4 ---------------------------------------------------------

    def test_s3_iso_4_commit_marker(self):
        """Markdown-first / state-last commit marker with real fault windows."""
        self.finalize_a_ok("s3-iso-4")
        md_path = self.prof_dir / CANDIDATES_MD
        state_path = self.prof_dir / CANDIDATE_STATE
        old_md, old_state = md_path.read_bytes(), state_path.read_bytes()
        a_results = self.write_a_results("s3-iso-4-reuse")
        # A changed profile makes the re-render deterministically different
        # from the old bytes (render header 校准 flip), so "new Markdown
        # installed" is byte-observable even when the clock has not ticked.
        profile = self.root / "iso4-profile.md"
        profile.write_text("兴趣：第二种输入模式的比较\n", encoding="utf-8")
        profile_args = ("--profile", str(profile))

        # 1. Pause after the Markdown install, before the state replace: a
        #    concurrent reader sees the NEW Markdown already installed while
        #    the candidate state is still the OLD committed one, and the
        #    failing state replace restores both old byte sets.
        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader():
            self.assertTrue(attempted.wait(30))
            observed["state"] = state_path.read_bytes()
            observed["md"] = md_path.read_bytes()
            released.set()

        def gate(real, src, dst):
            if Path(dst) == state_path:
                attempted.set()
                self.assertTrue(released.wait(30))
                raise OSError("synthetic candidate-state install failure")

        watcher = threading.Thread(target=reader)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path), gate):
                payload, code = call_runner(
                    "stage3-finalize", "--professor-dir", self.prof_dir,
                    "--results", a_results, "--program-root", self.root,
                    *profile_args)
        finally:
            watcher.join(30)
        self.assertEqual(payload["reason_code"], "local_pair_commit_failed", payload)
        self.assertEqual(observed["state"], old_state,
                         "a reader before the commit point saw new state bytes")
        self.assertNotEqual(observed["md"], old_md,
                            "the new Markdown was not installed before the "
                            "state replace: install order not observable")
        self.assertEqual(md_path.read_bytes(), old_md)
        self.assertEqual(state_path.read_bytes(), old_state)

        # 2. Release the state replace: the reader only after the atomic
        #    replace sees the NEW committed state whose render SHA matches
        #    the installed Markdown body.
        attempted, released = threading.Event(), threading.Event()
        observed = {}

        def reader_after_install():
            self.assertTrue(attempted.wait(30))
            observed["state"] = json.loads(state_path.read_text(encoding="utf-8"))
            released.set()

        def install_then_release(real, src, dst):
            real(src, dst)  # the atomic install has happened at this point
            attempted.set()
            self.assertTrue(released.wait(30))

        watcher = threading.Thread(target=reader_after_install)
        watcher.start()
        try:
            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(state_path),
                    install_then_release):
                payload, code = call_runner(
                    "stage3-finalize", "--professor-dir", self.prof_dir,
                    "--results", a_results, "--program-root", self.root,
                    *profile_args)
        finally:
            watcher.join(30)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        _, md_body = contact_state.split_frontmatter(
            md_path.read_text(encoding="utf-8"))
        self.assertEqual(observed["state"]["cache"]["render"][CANDIDATES_MD]["sha256"],
                         contact_state.sha256_text(md_body))

        # 3. Post-commit cleanup unlink failure: both new byte sets stay, the
        #    committed transaction is not rolled back or re-framed. A second
        #    profile makes this transaction's content deterministically
        #    different from the previous run's committed pair (the frontmatter
        #    state_fingerprint binds the profile), so retention of the NEW
        #    bytes is provable even within the same second.
        previous_md = md_path.read_bytes()
        previous_state_bytes = state_path.read_bytes()
        previous_state = json.loads(previous_state_bytes)
        profile2 = self.root / "iso4-profile-2.md"
        profile2.write_text("兴趣变化：第二种输入模式的扩展比较\n", encoding="utf-8")
        profile2_args = ("--profile", str(profile2))
        staged_prefixes = (f".{CANDIDATES_MD}.", f".{CANDIDATE_STATE}.")
        owner_dir = os.path.realpath(self.prof_dir)

        def cleanup_target(path):
            return (os.path.dirname(path) == owner_dir
                    and Path(path).name.startswith(staged_prefixes))

        with failing_unlink(cleanup_target):
            payload, code = call_runner(
                "stage3-finalize", "--professor-dir", self.prof_dir,
                "--results", a_results, "--program-root", self.root,
                *profile2_args)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        current_state = json.loads(state_path.read_text(encoding="utf-8"))
        _, md_body = contact_state.split_frontmatter(
            md_path.read_text(encoding="utf-8"))
        self.assertEqual(current_state["cache"]["render"][CANDIDATES_MD]["sha256"],
                         contact_state.sha256_text(md_body))
        # Review C2: the old pair is self-consistent too, so consistency
        # alone cannot prove retention. Both retained files must be THIS
        # transaction's new content — not the previous run's committed pair
        # (a cleanup-failure rollback would restore exactly those bytes).
        self.assertNotEqual(md_path.read_bytes(), previous_md,
                            "cleanup failure must not roll the local Markdown "
                            "back to the previous run's bytes")
        self.assertNotEqual(state_path.read_bytes(), previous_state_bytes,
                            "cleanup failure must not roll the candidate state "
                            "back to the previous run's bytes")
        self.assertNotEqual(current_state["profile_fingerprint"],
                            previous_state["profile_fingerprint"])
        self.assertEqual(current_state["profile_fingerprint"],
                         contact_state.profile_fingerprint(str(profile2)))
        self.assertIn("profile：有", md_path.read_text(encoding="utf-8"))

    # -- S3-ISO-5 ---------------------------------------------------------

    def test_s3_iso_5_aggregate_identity_derivation(self):
        """Same display name / IDs across professors stay separate rows."""
        self.build_twin_professor()
        a_results = self.write_a_cross(self.write_a_results("s3-iso-5-a"))
        out = self.stage3_finalize(a_results, "--cross-direction-groups",
                                   CROSS_GROUP_ARG)
        self.assertEqual(out["status"], "ok",
                         msg=json.dumps(out, ensure_ascii=False))
        self.finalize_twin_ok(priority_a="主推 候选1（Y分野）", cross_count=2)
        a_state = self.prof_dir / CANDIDATE_STATE
        twin_state = self.twin_dir / CANDIDATE_STATE
        # Local Markdowns are manually corrupted AFTER the commits: the
        # overview must not take a single fact from them.
        for path in (self.prof_dir / CANDIDATES_MD, self.twin_dir / CANDIDATES_MD):
            path.write_text(path.read_text(encoding="utf-8") + "\n与状态矛盾的人工行\n",
                            encoding="utf-8")
        states_before = self.snapshot(a_state, twin_state)

        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["professor_count"], 2)
        body = self.overview_business_body()
        a_link = "X分野/試験 教授/套磁想法候选.md"
        twin_link = "Y分野/試験 教授/套磁想法候选.md"
        # One direction row per (canonical professor, direction), values from
        # each committed state; the corrupted Markdown contributes only links.
        self.assertIn(f"| 試験 教授 | 信号処理 | 3 | 主推 1 | [{CANDIDATES_MD}]({a_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | 信号処理 | 4 | 主推 候选1（Y分野） | [{CANDIDATES_MD}]({twin_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | センサ網 | 3 | 主推 1 | [{CANDIDATES_MD}]({a_link}) |", body)
        self.assertIn(f"| 試験 教授 | センサ網 | 3 | 并推 Twin | [{CANDIDATES_MD}]({twin_link}) |", body)
        # Cross rows keep the same group ID for both professors, and each
        # row's candidate count comes from its OWN committed state (1 vs 2).
        self.assertIn(f"| 試験 教授 | 跨方向：dir_A＋dir_B | 1 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({a_link}) |",
                      body)
        self.assertIn(f"| 試験 教授 | 跨方向：dir_A＋dir_B | 2 | 显式跨方向组（group_id {CROSS_GID}） | [{CANDIDATES_MD}]({twin_link}) |",
                      body)
        self.assertNotIn("与状态矛盾的人工行", body)
        # Stable ordering: canonical professor identity is the tie-breaker.
        self.assertLess(body.index(a_link), body.index(twin_link))
        self.assert_unchanged(states_before)

        # Delete + rebuild derives the same business rows/links from the
        # committed states alone (only the generation time may differ).
        self.overview_path.unlink()
        out2 = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out2["status"], "ok", out2)
        self.assertEqual(self.overview_business_body(), body)
        self.assert_unchanged(states_before)

    # -- S3-ISO-6 ---------------------------------------------------------

    def test_s3_iso_6_rebuild_failure_legacy(self):
        """Every rebuild failure preserves bytes; legacy identity is strict."""
        self.finalize_a_ok("s3-iso-6-a")
        b_state_path = self.build_second_professor() / CANDIDATE_STATE
        b_pack_path = self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / "套磁候选输入.json"
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        # Local files of BOTH professors plus the aggregate artifacts: every
        # failure sub-scenario must leave all of them byte-identical.
        snapshot_paths = (self.prof_dir / CANDIDATE_STATE,
                          self.prof_dir / CANDIDATES_MD,
                          b_state_path,
                          self.root / "教授研究" / "Y分野" / SECOND_PROFESSOR / CANDIDATES_MD,
                          self.overview_path, self.registry_path)
        legacy_candidate = {"id": "C1", "title": "旧候选", "one_liner": "一句话",
                            "research_question": "旧的问题", "points": [],
                            "gap_ids": [], "papers": [], "fit": "high",
                            "fit_note": "", "why_recommended": "旧理由",
                            "tension_points": []}

        def write_b_state(payload):
            b_state_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        original_b_state = b_state_path.read_text(encoding="utf-8")
        original_b_pack = b_pack_path.read_text(encoding="utf-8")
        try:
            # (a) malformed committed state → fail before any write.
            b_state_path.write_text("{ malformed", encoding="utf-8")
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertIn("invalid", out["reason_code"])
            self.assert_unchanged(before)

            # (b) legacy collection_key with 0 canonical matches → fail closed
            #     with legacy_direction_identity before any write.
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "CK_UNKNOWN",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"CK_UNKNOWN": "legacy-fp"}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "legacy_direction_identity")
            self.assert_unchanged(before)

            # (c) 1-match legacy identity migrates in memory only: rebuild
            #     succeeds, the v1 state file itself stays byte-identical.
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "dir_C",
                                           "name_ja": "対照", "name_zh": "对照",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"dir_C": "legacy-fp"}})
            b_bytes = b_state_path.read_bytes()
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            self.assertIn(
                f"| {SECOND_PROFESSOR} | 対照 | 1 | — | "
                f"[{CANDIDATES_MD}](Y分野/{SECOND_PROFESSOR}/{CANDIDATES_MD}) |",
                self.overview_business_body())
            self.assertEqual(b_state_path.read_bytes(), b_bytes)

            # (d) two pack directions sharing the referenced collection_key →
            #     multi-match fails closed before any write.
            pack = json.loads(original_b_pack)
            duplicate = json.loads(json.dumps(pack["directions"][0]))
            duplicate["direction_id"] = "dir_D"
            duplicate["name_ja"] = "第二方向"
            pack["directions"].append(duplicate)
            write_json(b_pack_path, pack)
            write_b_state({"schema": 1, "professor": SECOND_PROFESSOR,
                           "directions": [{"collection_key": "dir_C",
                                           "candidates": [legacy_candidate]}],
                           "input_fingerprints": {"dir_C": "legacy-fp"}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "legacy_direction_identity")
            self.assert_unchanged(before)

            # (d2) review D1: a v2 state with valid schema/kind/identity
            #      stamps but a structurally corrupt directions container
            #      fails closed BEFORE any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": {"dir_C": {"candidates": []}}})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d3) review D1: candidates as a non-list on a stamped v2 row —
            #      the count basis is corrupt, so the rebuild must stop and
            #      preserve the old overview.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "candidates": "garbage"}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d4) review D1: a cross group without a machine group identity
            #      fails closed before any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C", "candidates": []}],
                           "cross_direction_groups": [{"direction_ids": ["dir_C"],
                                                        "candidates": []}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d5) review C1: a null candidate list on a stamped v2 row is
            #      CORRUPT, not zero candidates — the rebuild must fail
            #      closed instead of publishing a count-0 row.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "name_ja": "対照", "name_zh": "对照",
                                           "candidates": None}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (d6) review C1: non-list candidate members and null group
            #      fields fail closed before any overview write.
            write_b_state({"schema": contact_state.CANDIDATE_STATE_SCHEMA,
                           "kind": contact_state.CANDIDATE_STATE_KIND,
                           "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
                           "generator_contract_version":
                               contact_state.STAGE3_GENERATOR_CONTRACT_VERSION,
                           "professor": SECOND_PROFESSOR,
                           "directions": [{"direction_id": "dir_C",
                                           "candidates": [None, "garbage"]}],
                           "cross_direction_groups": [
                               {"group_id": "cross:abc", "direction_ids": None,
                                "candidates": None}]})
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "error", out)
            self.assertEqual(out["reason_code"], "invalid_candidate_state")
            self.assert_unchanged(before)

            # (e) manual overview conflict fails the rebuild, keeps the edit.
            b_state_path.write_text(original_b_state, encoding="utf-8")
            b_pack_path.write_text(original_b_pack, encoding="utf-8")
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            self.overview_path.write_text(
                self.overview_path.read_text(encoding="utf-8") + "\n人工改动\n",
                encoding="utf-8")
            manual = self.overview_path.read_bytes()
            before = self.snapshot(*snapshot_paths)
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "needs_decision", out)
            self.assertEqual(out["reason_code"], "manual_markdown_changed")
            self.assert_unchanged(before)
            self.assertEqual(self.overview_path.read_bytes(), manual)

            # (f) final-replace I/O failure keeps the old overview bytes.
            self.overview_path.unlink()
            out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
            self.assertEqual(out["status"], "ok", out)
            before = self.snapshot(*snapshot_paths)

            def explode(real, src, dst):
                raise OSError("synthetic overview install failure")

            with gated_os_replace(
                    lambda src, dst: dst == os.path.realpath(self.overview_path),
                    explode):
                payload, code = call_runner(
                    "stage3-rebuild-overview", "--program-root", self.root)
            self.assertEqual(payload["reason_code"], "overview_write_failed", payload)
            self.assert_unchanged(before)
        finally:
            b_state_path.write_text(original_b_state, encoding="utf-8")
            b_pack_path.write_text(original_b_pack, encoding="utf-8")

    # -- S3-ISO-7 ---------------------------------------------------------

    def test_s3_iso_7_registry_stage4_source(self):
        """Registry independence for rebuild + Stage 4 keeps its local source."""
        self.finalize_a_ok("s3-iso-7")
        a_state = self.prof_dir / CANDIDATE_STATE
        selection = {"professor": PROFESSOR, "professor_dir": str(self.prof_dir),
                     "direction_ids": ["dir_A"],
                     "ideas": [{"id": "dir_A_1", "note": "主推"}]}

        def stale_managed_overview():
            body_old = "# 套磁想法候选总览\n\n旧一代聚合。\n"
            sha_old = contact_state.sha256_text(body_old)
            fingerprint = contact_state.sha256_obj(
                {"projection": CANDIDATES_OVERVIEW, "body": sha_old})
            self.overview_path.write_text(
                contact_state.render_frontmatter(fingerprint, sha_old) + body_old,
                encoding="utf-8")

        # Overview missing → generated; registry missing before and after.
        self.assertTrue(not self.registry_path.exists())
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertFalse(self.registry_path.exists())

        # Stale but managed overview → rebuildable and refreshed.
        stale_managed_overview()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertIn(PROFESSOR, self.overview_business_body())

        # Corrupt (frontmatter gone) → fail closed, bytes unchanged.
        self.overview_path.write_text("被破坏的总览\n", encoding="utf-8")
        broken = self.overview_path.read_bytes()
        out = run_cli("stage3-rebuild-overview", "--program-root", self.root)
        self.assertEqual(parse(out)["reason_code"], "manual_markdown_changed")
        self.assertEqual(self.overview_path.read_bytes(), broken)

        # Restore a managed overview, then prove registry independence:
        # malformed / stale registry → no read, no write, no side effect.
        self.overview_path.unlink()
        rebuild_ok = parse(run_cli("stage3-rebuild-overview",
                                   "--program-root", self.root))
        self.assertEqual(rebuild_ok["status"], "ok")
        self.overview_path.unlink()
        self.registry_path.write_text("{ malformed registry", encoding="utf-8")
        malformed = self.registry_path.read_bytes()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(self.registry_path.read_bytes(), malformed)
        self.registry_path.write_text(
            json.dumps({"render": {"套磁邮件总览.md": {"sha256": "old"}}},
                       ensure_ascii=False),
            encoding="utf-8")
        stale_registry = self.registry_path.read_bytes()
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(self.registry_path.read_bytes(), stale_registry)

        # Low-level proof: a rebuild never even opens the registry.
        with OpenRecorder() as recorder:
            payload, code = call_runner(
                "stage3-rebuild-overview", "--program-root", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok", payload)
        self.assertFalse(recorder.was_opened(self.registry_path))
        self.assertTrue(recorder.was_opened(a_state))

        # Stage 4 keeps joining the professor-local state under every
        # overview anomaly (missing / stale / corrupt).
        for condition in ("missing", "stale", "corrupt"):
            with self.subTest(overview=condition):
                if self.overview_path.exists():
                    self.overview_path.unlink()
                if condition == "stale":
                    stale_managed_overview()
                elif condition == "corrupt":
                    self.overview_path.write_text("被破坏的总览\n", encoding="utf-8")
                overview_before = self.snapshot(self.overview_path)
                sel_input = self.root / f"sel-input-{condition}.json"
                sel_input.write_text(json.dumps({"selections": [selection]},
                                                ensure_ascii=False),
                                     encoding="utf-8")
                out4 = parse(run_cli("stage4-finalize", "--program-root", self.root,
                                     "--selection-input", sel_input))
                self.assertEqual(out4["status"], "ok", out4)
                pack = json.loads((self.root / "教授研究" / "邮件输入.json")
                                  .read_text(encoding="utf-8"))
                email = next(e for e in pack["emails"]
                             if e["email_id"] == f"{PROFESSOR}::dir_A::dir_A_1")
                self.assertEqual(
                    {(g["direction_id"], g["item_key"], g["gap_id"])
                     for g in email["gaps"]},
                    {("dir_A", "P1", self.gap_ids["P1"])})
                self.assert_unchanged(overview_before)

    # -- S3-COMP-1 --------------------------------------------------------

    @staticmethod
    def machine_projection(state):
        """Volatile-field-free projection of the candidate machine contract."""
        return {
            "schema": state["schema"], "kind": state["kind"],
            "identity_version": state["identity_version"],
            "generator_contract_version": state["generator_contract_version"],
            "professor": state["professor"],
            "profile_fingerprint": state["profile_fingerprint"],
            "input_fingerprints": state["input_fingerprints"],
            "directions": [{"direction_id": d["direction_id"],
                            "stage3_status": d["stage3_status"],
                            "candidates": [{"id": c["id"], "kind": c["kind"],
                                            "direction_ids": c["direction_ids"],
                                            "gap_refs": c["gap_refs"],
                                            "papers": [p["item_key"]
                                                       for p in c["papers"]]}
                                           for c in d["candidates"]]}
                           for d in state["directions"]],
            "cross_direction_groups": [{"group_id": g["group_id"],
                                         "direction_ids": g["direction_ids"],
                                         "direction_fingerprints":
                                             g["direction_fingerprints"],
                                         "profile_fingerprint":
                                             g["profile_fingerprint"],
                                         "candidates": [c["id"]
                                                        for c in g["candidates"]]}
                                        for g in state["cross_direction_groups"]],
        }

    def test_s3_comp_1_preserved_candidate_contract(self):
        """Two directions + one cross group keep the frozen machine contract."""
        results = self.write_a_cross(self.write_a_results("s3-comp-1"))
        out = self.stage3_finalize(results, "--cross-direction-groups",
                                   CROSS_GROUP_ARG)
        self.assertEqual(out["status"], "ok", out)
        state_path = self.prof_dir / CANDIDATE_STATE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        projection = self.machine_projection(state)
        self.assertEqual(projection["schema"], 2)
        self.assertEqual([d["direction_id"] for d in projection["directions"]],
                         ["dir_A", "dir_B"])
        self.assertEqual(projection["cross_direction_groups"][0]["group_id"],
                         CROSS_GID)
        self.assertEqual(projection["cross_direction_groups"][0]["direction_ids"],
                         ["dir_A", "dir_B"])

        # Validator round 1 fails the dir_A scope and the cross-group scope
        # (both proven from the rendered text), so the correction round
        # re-renders both and the group survives the correction finalize.
        validation = self.root / "comp1-validation.json"
        finding = {"rule": "B5", "severity": "blocking",
                   "location": "validator 自报位置", "quote": "",
                   "suggestion": "首次出现时用日常语言解释。"}
        dir_a_finding = dict(finding, quote="候选 dir_A_1")
        cross_finding = dict(finding, quote="候选 XA")
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "fail", "blocking": 2, "minor": 0,
            "issues": [dir_a_finding, cross_finding]}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], True, record)
        block = json.loads(state_path.read_text(encoding="utf-8"))["validator"]
        self.assertEqual(set(block["pending"]),
                         {"direction:dir_A", f"group:{CROSS_GID}"})
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")

        # Correction rerender: wording/priority repaired, machine projection
        # frozen, unprocessed scopes keep their proofs, render SHA carried.
        revised = self.generated_doc("dir_A", ["P1", "P2", None])
        revised["priority"] = "主推 候选1（修订版）"
        write_json(results / result_file("candidates", "dir_A"), revised)
        out = self.stage3_finalize(results, "--validation-file", validation)
        self.assertEqual(out["status"], "ok", out)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(self.machine_projection(state), projection)
        block = state["validator"]
        self.assertEqual(block["round"], 1)
        self.assertEqual(block["render_sha256"],
                         state["cache"]["render"][CANDIDATES_MD]["sha256"])
        self.assertIn("dir_B", block["results"])
        self.assertEqual(block["results"]["dir_B"]["result"], "pass")
        self.assertEqual(block["groups"], {})
        self.assertEqual(block["pending"], {})

        # Round 2 on the corrected render is the terminal record.
        write_json(validation, {"result": "ok", "files": [{
            "file": str(self.prof_dir / CANDIDATES_MD), "artifact": "candidates",
            "verdict": "pass", "blocking": 0, "minor": 0, "issues": []}]})
        record = parse(run_cli("stage3-record-validation", "--professor-dir",
                               self.prof_dir, "--validation-file", validation))
        self.assertEqual(record["needs_correction"], False, record)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["validator"]["results"]["dir_A"]["result"], "pass")
        self.assertEqual(state["validator"]["results"]["dir_A"]["rounds"], 2)

    # -- S3-DEP-1 ---------------------------------------------------------

    def test_s3_dep_1_no_issue48_lock_dependency(self):
        """#48 writer lock is not a prerequisite anywhere on the #66 path."""
        source = _SCRIPT.read_text(encoding="utf-8")
        rebuild_source = inspect.getsource(contact_state.cmd_stage3_rebuild_overview)
        finalize_source = inspect.getsource(contact_state.cmd_stage3_finalize)
        lock_pattern = re.compile(
            r"\block\b|\bflock\b|O_EXCL|FileLock|portalocker|state_writer_busy"
            r"|professor-contact-state\.lock|lockf|writer_registry")
        for label, text in (("module", source), ("rebuild", rebuild_source),
                            ("finalize", finalize_source)):
            with self.subTest(target=label):
                self.assertIsNone(lock_pattern.search(text),
                                  f"{label} must not reference writer-lock machinery")

        # Dynamic: finalize + rebuild run with no lock fixture and create no
        # lock artifacts anywhere in the program root.
        self.finalize_a_ok("s3-dep-1")
        out = parse(run_cli("stage3-rebuild-overview", "--program-root", self.root))
        self.assertEqual(out["status"], "ok", out)
        lock_files = [p for p in self.root.rglob("*")
                      if p.is_file() and (p.name.endswith(".lock")
                                          or ".lock." in p.name)]
        self.assertEqual(lock_files, [])

    # -- S3-DOC-1 ---------------------------------------------------------

    def test_s3_doc_1_caller_lifecycle(self):
        """Static caller/lifecycle/owner contract across Skill, agent, runner."""
        skill = SKILL_PATH.read_text(encoding="utf-8")
        agent = AGENT_PATH.read_text(encoding="utf-8")
        wfref = WFREF_PATH.read_text(encoding="utf-8")

        start = skill.index("### Stage 3/4 编排边界")
        end = skill.find("\n### ", start + 1)
        section = skill[start:end if end > 0 else len(skill)]
        # Exactly one rebuild owner/call point per runtime.
        self.assertEqual(section.count("stage3-rebuild-overview"), 2)
        opencode_bullet = section[section.index("- **OpenCode（OpenCode-only 嵌套路径）**"):
                                  section.index("- **Codex（root caller")]
        codex_bullet = section[section.index("- **Codex（root caller"):]
        self.assertIn("stage3-rebuild-overview", opencode_bullet)
        self.assertIn("idea-generator 自己", opencode_bullet)
        self.assertIn("不反转 local terminal", opencode_bullet)
        self.assertIn("不为修总览重跑 finalize", opencode_bullet)
        self.assertIn("stage3-rebuild-overview", codex_bullet)
        self.assertIn("root caller 自己 best-effort 运行一次", codex_bullet)
        self.assertIn("不反转 local terminal", codex_bullet)
        self.assertIn("不得事后修改它", codex_bullet)
        # The validator loop and 2-round cap stay load-bearing in the section.
        for required in ("最多 2 次 style-validator", "stage3-record-validation",
                         "professor-contact-style-validator"):
            self.assertIn(required, section)
        # overview_md is a target path, never the verdict.
        self.assertIn("`overview_md` 不是成功证据", section)
        self.assertIn("永远不是 rebuild 成功证据", agent)
        # The read-first completion gate also carries the terminal rebuild.
        header = skill[:skill.index("## What this is for")]
        self.assertIn("stage3-rebuild-overview", header)
        # Stage 4 keeps consuming the candidate state, not the overview.
        self.assertIn("用户从**候选状态**（非 Markdown）挑选", skill)
        # The workflow reference freezes the projection boundary.
        self.assertIn("stage3-rebuild-overview", wfref)
        self.assertIn("派生投影", wfref)

        # Review r11 (plan issue-66-plan-r11-2026-10-02 §4-§6): the Codex
        # state machine, stop points, 2/4 sibling bound and the raw
        # validator handoff are load-bearing contract text.
        self.assertIn("Codex Stage 3 固定状态转移", section)
        self.assertIn("G1 → V1 → record(V1)", section)
        self.assertIn("G2(validation_file = V1 原始 JSON)", section)
        self.assertIn("root 直属 Stage-3 child 总数只能是 2 或 4", section)
        self.assertIn("第 5 个 child 一律是 caller contract violation", section)
        self.assertGreaterEqual(section.count("立即停止 Stage 3"), 2)
        self.assertIn("不得用 `printf`/模板重打", section)
        self.assertIn("无重构权", section)
        # Last-mile handoff: byte-exact on-disk content, declined-channel
        # retry rule, and the post-run transcript comparison.
        self.assertIn("落盘字节必须与 child 消息逐字节相同", section)
        self.assertIn("不得新增结尾换行", section)
        self.assertIn("换一条通道把同一份原话重写一遍", section)
        self.assertIn("逐字节比对", section)
        # OpenCode bullet carries the same-round source binding and the
        # early-stop on any runner non-success.
        self.assertIn("每一轮只解析一次 profile/source tuple", opencode_bullet)
        self.assertIn("同一 `--profile <abs>`", opencode_bullet)
        self.assertIn("立即结束并把结构化失败返回 caller", opencode_bullet)
        # Agent doc: hard source-binding preconditions with the plan
        # fingerprint check and runner non-success early stop.
        self.assertIn("Source binding（执行前硬条件", agent)
        self.assertIn("profile_fingerprint_binding_failed", agent)
        self.assertIn("runner 非成功早停", agent)
        self.assertIn("原样完整落盘", agent)
        self.assertIn("绝不手写 `printf`/模板重打", agent)
        # Agent doc: the binding branch itself, not just its marker strings
        # (issue-66 gate2 r15 revision; closes 5978275031 / 5978453336).
        ok, why = _doc_binding_disposition(agent)
        self.assertTrue(
            ok, f"agent binding branch fails the frozen judgment: {why}")
        # The judgment above has to reject the historical defects it replaces
        # and the concordance gap found in this revision: the unconditional
        # non-empty demand (8fe6f96), the fingerprint read from the finalize
        # response (edc39f6), and an instruction that lets the committed
        # fingerprint differ from the plan fingerprint.  Each mutation is cut
        # into the current frozen paragraph, so a judgment that merely accepts
        # the current text is caught here.
        frozen = next((line for line in agent.splitlines()
                       if _STEP3_START.search(line)), None)
        self.assertIsNotNone(frozen, "frozen binding paragraph not found")
        guard = _BRANCH_WITH_PROFILE.search(frozen)
        no_guard = _BRANCH_NO_PROFILE.search(frozen)
        self.assertIsNotNone(guard, "profile-present branch condition missing")
        self.assertIsNotNone(no_guard, "no-profile branch condition missing")
        plan_line = next((line for line in agent.splitlines()
                          if "plan 指纹硬检查" in line), None)
        self.assertIsNotNone(plan_line, "plan-side hard check not found")
        # The mutation anchors are located by pattern; the behaviour itself is
        # judged by _doc_binding_disposition, so no Chinese sentence is pinned
        # as the acceptance wording (issue-66 gate2 revision, 2026-10-04 19:19).
        source_clause = re.search(r"finalize 成功[^。；\n]{0,80}?state_path[^。；\n]{0,40}",
                                  frozen)
        self.assertIsNotNone(source_clause, "committed-state source clause not found")
        good_source = source_clause.group()
        plan_clause = re.search(r"存在 profile 时[^。；\n]{0,80}", plan_line)
        self.assertIsNotNone(plan_clause, "plan-side profile clause not found")
        plan_strong = plan_clause.group()
        # The boundary that closes the profile-present branch condition is
        # derived from the guard structure, not from a pinned sentence, so a
        # standalone cancelling sentence can be placed right after it.
        command_prefix = re.search(r"本命令的[^。；\n]{0,4}`--profile`", frozen[guard.end():])
        self.assertIsNotNone(command_prefix, "profile-present branch command not found")
        # The branch condition closes here; a cancelling sentence placed after
        # this point sits in front of the parts that carry the binding markers.
        guard_end = frozen[guard.start():guard.end() + 1]
        self.assertTrue(guard_end.endswith("时，"),
                        "profile-present branch boundary not found")
        # The concordance and read-failure spans are located by pattern, so no
        # single Chinese sentence is frozen as the acceptance wording.
        concordance_match = _CONCORDANCE_SENTENCE.search(frozen)
        self.assertIsNotNone(concordance_match, "concordance wording not found")
        # Replace only the clause that carries the demand, so the paragraph
        # anchors and the rest of the rule stay untouched.
        clause_sep = "——"
        sentence_start = frozen.rfind(clause_sep, 0, concordance_match.start()) + len(clause_sep)
        sentence_end = frozen.find(clause_sep, concordance_match.end())
        sentence_end = len(frozen) if sentence_end < 0 else sentence_end
        concordance = frozen[sentence_start:sentence_end]
        # The read-failure wording is located by pattern too.
        read_fail_match = _READ_FAIL_WORDING.search(frozen)
        self.assertIsNotNone(read_fail_match, "read-failure stop point not found")
        read_fail_stop = read_fail_match.group()
        self.assertIn("读取失败", read_fail_stop)
        mutations = {
            # The 8fe6f96 defect: the branch guard dropped, so the frozen
            # stop rule applies to every round, no-profile rounds included.
            "unconditional_nonempty": agent.replace(guard.group(), ""),
            # The edc39f6 defect: source switched to the finalize response.
            "wrong_response_source": agent.replace(
                good_source,
                "读取 `stage3-finalize` 返回的 `profile_fingerprint`"),
            # No-profile branch re-armed with a stop / non-empty demand.
            "no_profile_stop": agent.replace(
                "**不报错、不停止**",
                "**不报错**，`profile_fingerprint` 为 `null` 时一律停止并返回 error"),
            "no_profile_nonempty": agent.replace("合法结果", "必须是非空字符串"),
            # Plan-side hard check loses the scope / the non-empty demand.
            "plan_scope_removed": agent.replace(
                plan_line, plan_line.replace(
                    plan_strong, "必须与已解析 profile 一致")),
            "plan_nonempty_removed": agent.replace(
                plan_line, plan_line.replace(
                    plan_strong, "必须绑定本 child 传入的同一 `--profile`")),
            # The plan-side stop point is dropped from the fail-closed text.
            "plan_stop_removed": agent.replace(
                "plan 侧空指纹必须停在写任何候选 result 文件之前（Step 1.5），",
                "plan 侧空指纹按绑定失败处理，"),
            # The concordance clause is rewritten to cancel the comparison, and
            # the mismatch stop point is dropped (the counterexample in the
            # 2026-10-04 18:00 review).
            "concordance_cancelled": agent.replace(
                concordance,
                "它必须是非空字符串且与 plan 返回的 `profile_fingerprint` 完全一致，"
                "但实际执行无需比较这两个指纹"
            ).replace(read_fail_stop, "状态文件读取失败"),
            # A cancellation written as "need not carry out a comparison of the
            # committed fingerprint and the plan fingerprint" (the
            # counterexample in the 2026-10-04 19:19 review).
            "skip_comparison_verb": agent.replace(
                guard_end, "时。本轮无需对提交状态指纹与 `plan` 指纹进行比较。本命令的"),
            # The same shape with other cancellation wording.
            "skip_comparison_check": agent.replace(
                guard_end, "时。本轮不必对提交状态指纹与计划指纹做核对。本命令的"),
            # The cancellation arrives after a still-positive agreement wording
            # (the counterexample in the 2026-10-04 18:24 review).
            "tail_cancellation": agent.replace(
                concordance,
                "它必须是非空字符串且与 plan 返回的 `profile_fingerprint` 完全一致，"
                "但实际执行无需比较这两个指纹"),
            # A standalone cancelling sentence placed in front of the parts that
            # carry the binding markers (the counterexample in the 2026-10-04
            # 19:01 review).
            "prefix_sentence_cancellation": agent.replace(
                guard_end, "时。本轮无需比较提交状态指纹与 plan 指纹。本命令的 `--profile`"
                " 必须逐字复用"),
            # The same shape with different cancellation wording.
            "prefix_sentence_needs_no_comparison": agent.replace(
                guard_end, "时。本轮不必比较提交状态指纹与计划指纹。本命令的 `--profile`"
                " 必须逐字复用"),
            # The mismatch stop point alone is dropped, and the read-failure
            # stop point alone is dropped.
            "mismatch_stop_removed": agent.replace(
                "、状态文件读取失败或不一致", "、状态文件读取失败"),
            "read_failure_stop_removed": agent.replace(
                read_fail_stop, "状态文件不一致"),
        }
        # Note: dropping the concordance wording alone is not a defect — the
        # "mismatch -> stop" clause in the same rule still binds the committed
        # fingerprint to the plan one, and that clause is asserted above.
        for label, mutated in mutations.items():
            with self.subTest(mutation=label):
                self.assertNotEqual(mutated, agent,
                                    f"{label} mutation did not apply")
                ok, why = _doc_binding_disposition(mutated)
                self.assertFalse(ok, f"judgment accepted the {label} defect")
        # The unmutated document every mutation derives from stays the accepted
        # one, so the matrix cannot pass by rejecting everything.
        self.assertTrue(_doc_binding_disposition(agent)[0])
        # A legal rewrite that keeps the same demand in different words is
        # accepted: the contract is the behaviour, not one frozen sentence.
        for label, rewritten in {
                "plan 中文口径": "从该状态文件的 `profile_fingerprint` 字段取出的值必须"
                                 "与 `stage3-plan` 的 profile 指纹逐字相同",
                "显式要求比较": "它必须是非空字符串，且必须比较提交指纹与计划指纹",
                "其与计划指纹一致": "它必须是非空字符串，且其与计划指纹一致",
                "无需重复比较但仍须核对":
                    "本轮无需重复比较提交状态指纹与 `plan` 指纹；"
                    "finalize 后仍必须从 `state_path` 读取提交状态并核对一次，"
                    "结果必须与 plan 指纹完全一致",
        }.items():
            with self.subTest(equivalent_wording=label):
                variant = agent.replace(concordance, rewritten)
                self.assertNotEqual(variant, agent, f"{label} rewrite did not apply")
                ok, why = _doc_binding_disposition(variant)
                self.assertTrue(ok, f"equivalent wording rejected: {label} ({why})")
        # Equivalent rewrites of the committed-state source and of the plan-side
        # check are accepted too: the contract is the behaviour, so the same
        # requirement written in other words must not fail the case.
        equivalent_rewrites = {
            "状态来源改写":
                (good_source,
                 "`stage3-finalize` 成功后，根据返回的 `state_path` 打开对应状态文件，"
                 "读取其中实际提交的 `profile_fingerprint`"),
            "计划侧改写":
                (plan_strong,
                 "存在 profile 时，`stage3-plan` 回传的 profile 指纹必须非空，并且要绑定"
                 "本 child 传入的同一 `--profile`"),
        }
        for label, (pinned, rewritten) in equivalent_rewrites.items():
            with self.subTest(equivalent_check=label):
                variant = agent.replace(pinned, rewritten, 1)
                self.assertNotEqual(variant, agent, f"{label} rewrite did not apply")
                ok, why = _doc_binding_disposition(variant)
                self.assertTrue(ok, f"equivalent {label} rejected: {why}")
        # plan r11 §4 facts, proved one by one: the frozen input binding must
        # be judged as a table instead of one marker at a time (review
        # 2026-10-04 20:02).  A legal re-flow of the same paragraph has to pass
        # too, so a line break can never become a false failure.
        binding_rows = _binding_facts(agent, skill)
        for fact_id, ok, why in binding_rows:
            with self.subTest(source_binding_fact=fact_id):
                self.assertTrue(ok, f"{fact_id} failed: {why}")
        paragraph = _binding_paragraph(agent)
        self.assertIsNotNone(paragraph, "binding paragraph not found")
        wrapped = agent.replace(paragraph, paragraph.replace("；", "；\n", 2), 1)
        with self.subTest(source_binding_fact="reflowed paragraph"):
            self.assertNotEqual(wrapped, agent, "paragraph reflow did not apply")
            self.assertTrue(_doc_binding_disposition(wrapped)[0],
                            "a legal reflow of the binding paragraph was rejected")
            self.assertTrue(all(ok for _, ok, _ in _binding_facts(wrapped, skill)),
                            "a legal reflow broke the source-binding facts")
        for fact_id, label, mutated in _source_binding_mutation_cases(agent, skill):
            with self.subTest(source_binding_mutation=label):
                if mutated == skill or (mutated != agent
                                        and _binding_paragraph(mutated) is None):
                    docs = (agent, mutated)
                else:
                    docs = (mutated, skill)
                self.assertIn(fact_id,
                              [row_id for row_id, ok, _ in _binding_facts(*docs)
                               if not ok],
                              f"{label}: its fact still passed")
        # plan r11 §5-§7 facts: the Codex state machine, the raw validator
        # handoff and the terminal rebuild owner are judged as relations, so a
        # conflicting sentence is rejected even when every marker survives.
        for fact_id, ok, why in _state_machine_facts(agent, skill, wfref):
            with self.subTest(state_machine_fact=fact_id):
                self.assertTrue(ok, f"{fact_id} failed: {why}")
        for fact_id, target, label, mutated in _state_machine_mutation_cases(
                agent, skill, wfref):
            with self.subTest(state_machine_mutation=label):
                docs = {"agent": agent, "skill": skill, "wfref": wfref}
                self.assertNotEqual(mutated, docs[target],
                                    f"{label} mutation did not apply")
                docs[target] = mutated
                rows = _state_machine_facts(docs["agent"], docs["skill"], docs["wfref"])
                broken = [row_id for row_id, ok, _ in rows if not ok]
                self.assertIn(fact_id, broken,
                              f"{label}: its fact still passed")

        # Workflow reference syncs the state machine and the sibling bound.
        self.assertIn("generator source-binding", wfref)
        self.assertIn("固定状态转移", wfref)
        self.assertIn("只能是 2 或 4", wfref)
        self.assertIn("无字段重构、翻译或重打权", wfref)

        # Agent doc: OpenCode runs the rebuild after the terminal record;
        # Codex callers run it after the child returned.
        self.assertIn("stage3-rebuild-overview", agent)
        self.assertIn("由你在终局记录后运行", agent)
        self.assertIn("Codex 下 rebuild 由调用线程在你返回之后自己运行", agent)

        # Runner structure: rebuild consumes the compatibility owner and has
        # no second legacy-mapping owner or registry access; finalize keeps
        # the local pair commit and lost every program-level reference.
        rebuild_source = inspect.getsource(contact_state.cmd_stage3_rebuild_overview)
        finalize_source = inspect.getsource(contact_state.cmd_stage3_finalize)
        self.assertIn("strict_candidate_state(", rebuild_source)
        self.assertNotIn("key_to_did", rebuild_source)
        self.assertNotIn("ambiguous", rebuild_source)
        self.assertNotIn("PROJECTIONS_FILE", rebuild_source)
        self.assertNotIn("load_projections", rebuild_source)
        for forbidden in ("load_projections", "projection_write", "save_projections",
                          "projection_conflict", "render_candidates_overview"):
            self.assertNotIn(forbidden, finalize_source)
        self.assertIn("staged_pair_commit", finalize_source)


if __name__ == "__main__":
    unittest.main()
