"""Synthetic Issue-59 Stage-5 fixture support for the regression suite.

This module holds the synthetic contact-evidence writers and Stage-5 fixture
builders that used to live in ``test_contact_state.py``.  It is deliberately
not named ``test_*.py`` so ``python -m unittest discover -p 'test_*.py'``
never collects it: it defines no TestCase and only prepares fixtures.

``test_contact_state`` re-exports every public name below, so existing test
callers keep their old import path, and the Issue-81 fixture scripts import
this module instead of loading the whole regression suite.  The runner module
is loaded once per importing process and handed to the regression suite as
well, so ``test_contact_state.contact_state`` stays the same module object the
helpers here use.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "contact_state.py"

_runner_spec = importlib.util.spec_from_file_location("contact_state", SCRIPT)
contact_state = importlib.util.module_from_spec(_runner_spec)
_runner_spec.loader.exec_module(contact_state)


def quote_id(quote: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", quote)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stage5_templates(root: Path) -> tuple[Path, Path]:
    """Deterministic synthetic templates the Stage-5 renderer requires."""
    template = root / "synthetic-template.md"
    followup = root / "synthetic-followup-template.md"
    if not template.exists():
        template.write_text("{{大学}}／{{研究科}}／{{先生名}}先生\n{{出身校}} {{氏名}}\n{{入学年度}} {{入学月}} {{専攻}} {{学位}}\n{{兴趣段}}\n{{未来志向}}\n{{学習中}}\n{{志望}}", encoding="utf-8")
    if not followup.exists():
        followup.write_text("{{先生名}}先生\n{{大学}} {{研究科}} {{学位}}\n{{出身校}} {{氏名}}\n{{初回送信日}}\n{{研究主题}}\n{{メールアドレス}}", encoding="utf-8")
    return template, followup


def raw_cli(*arguments):
    """Run the CLI with exactly these arguments: no fixture-side inference."""
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                          text=True, capture_output=True, check=False)


# --- Issue-59 constants, synthetic evidence and Stage-5 fixture writers ---


ISSUE59_PROFESSOR = "試験 教授"
ISSUE59_OTHER_PROFESSOR = "佐藤 花子"
ISSUE59_DIRECTION_ID = "DIR00001"
ISSUE59_IDEA_ID = "DIR00001_1"
ISSUE59_PEER_IDEA_ID = "DIR00001_2"
ISSUE59_EMAIL_ID = "試験 教授::DIR00001::DIR00001_1"
ISSUE59_PEER_EMAIL_ID = "試験 教授::DIR00001::DIR00001_2"
ISSUE59_OTHER_EMAIL_ID = "佐藤 花子::DIR00001::DIR00001_1"
ISSUE59_IDEAS = {ISSUE59_EMAIL_ID: ISSUE59_IDEA_ID,
                 ISSUE59_PEER_EMAIL_ID: ISSUE59_PEER_IDEA_ID,
                 ISSUE59_OTHER_EMAIL_ID: ISSUE59_IDEA_ID}
ISSUE59_GAP_QUOTE = ("Future work will extend the synthetic comparison "
                     "to a second input pattern.")
ISSUE59_PAPER_TITLE = "Synthetic comparison of input patterns"
ISSUE59_EMAIL_ADDRESS = "faculty@example.test"
ISSUE59_STALE_DAYS = 45
# One owner-shaped source-state reason, used only to make professor B
# demonstrably stale inside the program-level checker report.
ISSUE59_B_STALE_REASON = "source_changed:papers_json:Y分野/佐藤 花子/papers.json"
ISSUE59_MALFORMED_JSON = "{ this is not the email state"
def issue59_checker_stub(stale=None, marker=None):
    """Deterministic stand-in for professor-research's ``contact_evidence.py``.

    ``stale`` maps a professor to the owner-shaped reason their *live source
    state* is out of date; the report stays program-level, so its top-level
    ``result`` goes stale as soon as any professor does. ``marker`` is written
    only by the rebuild branch, which lets a case prove that an unrelated
    professor never pulled Stage 5 into a rebuild.
    """
    return (
        "import json, os, sys\n"
        f"STALE = {json.dumps(dict(stale or {}), ensure_ascii=False)}\n"
        f"MARKER = {json.dumps(str(marker or ''), ensure_ascii=False)}\n"
        "artifact = json.load(open(os.path.join(sys.argv[1], '教授研究', "
        f"{json.dumps(contact_state.CONTACT_EVIDENCE_FILE)}), encoding='utf-8'))\n"
        "if '--check' in sys.argv:\n"
        "    entries = [{'name': r['professor']['name'],\n"
        "                'result': 'stale' if STALE.get(r['professor']['name']) else 'fresh',\n"
        "                'reasons': [STALE[r['professor']['name']]]\n"
        "                if STALE.get(r['professor']['name']) else []}\n"
        "               for r in artifact['professors']]\n"
        "    reasons = sorted({x for e in entries for x in e['reasons']})\n"
        "    print(json.dumps({'result': 'stale' if reasons else 'fresh',\n"
        "                      'reasons': reasons, 'professors': entries},\n"
        "                     ensure_ascii=False))\n"
        "else:\n"
        "    if MARKER:\n"
        "        open(MARKER, 'w', encoding='utf-8').write('rebuilt\\n')\n"
        "    print(json.dumps({'result': 'ok'}))\n")


def issue59_verified_at(days_ago: int = 1) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


# Computed once per process so repeated fixture calls stay byte-identical while
# remaining inside the runner's 30-day verify-cache window.
ISSUE59_VERIFIED_AT = issue59_verified_at()


def issue59_email_row(professor, professor_dir, *, idea_id=ISSUE59_IDEA_ID,
                      direction_id=ISSUE59_DIRECTION_ID,
                      name="合成输入比较", contact_evidence=None):
    """Build one legal Stage-4 email row through the producer compiler.

    The Issue-59 fixture owns only fixed synthetic Stage-4 source values. All
    derived handoff fields (identity, paper/gap projection, allowed sources,
    fingerprints carried into the row, and source_hash) come from
    compile_email_entry, so this fixture cannot drift into a shadow Stage-4
    producer.
    """
    professor_dir = Path(professor_dir)
    gap_id = quote_id(ISSUE59_GAP_QUOTE)
    input_fingerprint = contact_state.sha256_obj({
        "fixture": "issue59-stage4-input",
        "professor": professor,
        "direction_id": direction_id,
    })
    gap = {
        "gap_id": gap_id, "item_key": "AAAA1111",
        "paper_title": ISSUE59_PAPER_TITLE, "paper_year": 2023,
        "quote": ISSUE59_GAP_QUOTE,
        "translation_zh": f"中译：{ISSUE59_GAP_QUOTE[:24]}",
        "source": "Conclusion", "page": 8, "status": "open",
        "confidence": "high", "completed_part": None, "remaining_gap": None,
        "evidence": "无更晚论文实现该点（AAAA1111）",
    }
    credibility = {
        "verdict": "站得住", "mainline": "主线",
        "authorship_line": "corresponding_dominant", "note": "test",
    }
    pack_direction = {
        "direction_id": direction_id,
        "collection_key": direction_id,
        "name_ja": name,
        "name_zh": name,
        "user_note": "我想比较两种合成输入的处理结果。",
        "input_fingerprint": input_fingerprint,
        "supporting_item_keys": ["AAAA1111"],
        "named_keys": [],
        "resolved_addition_keys": [],
        "gap_shortlist": [gap],
        "gaps_excluded": [],
        "completed_gap_blacklist": [],
        "red_lines": [{
            "scope": "global", "text": "不得引用未提供来源的数字",
            "banned_phrases": ["99.9%"],
        }],
        "credibility": credibility,
        "narrative": {
            "positioning": [{
                "text": (f"教授从 {{P:AAAA1111}} 起研究合成输入比较；"
                         f"{{G:{gap_id}}} 是延伸点。"),
            }],
        },
    }
    pack = {
        "professor": professor,
        "professor_dir": str(professor_dir),
        "papers": {
            "AAAA1111": {
                "item_key": "AAAA1111",
                "title": ISSUE59_PAPER_TITLE,
                "year": 2023,
                "authorship": "corresponding",
            },
        },
        "directions": [pack_direction],
    }
    idea = {
        "id": idea_id,
        "title": "第二种输入模式的合成比较",
        "idea_zh": "",
        "direction_ids": [direction_id],
        "papers": [{
            "item_key": "AAAA1111",
            "direction_ids": [direction_id],
            "fit_note": "教授通讯",
        }],
        "gap_refs": [{
            "direction_id": direction_id,
            "item_key": "AAAA1111",
            "gap_id": gap_id,
        }],
        "red_lines": [],
        "banned_phrases": [],
        "_profile_fields": {},
    }
    # compile_email_entry currently does not consume program_root, but pass the
    # semantic root so the fixture remains correct if that helper begins using
    # it later.
    program_root = professor_dir.parents[2]
    return contact_state.compile_email_entry(
        pack, {}, pack_direction, idea, "", program_root, None,
        contact_evidence=contact_evidence)


def issue59_result(gap_id, email_id=ISSUE59_EMAIL_ID, idea_id=ISSUE59_IDEA_ID):
    return {"schema": 1, "kind": "email", "email_id": email_id,
            "interest_sentences_ja": [
                "合成输入を比较する仕組みを、分かりやすく検証できる形にしたいと考えてきました。",
                "先生のご論文「Synthetic comparison of input patterns」を拝読し、入力比較を広げる可能性に気づかされました。",
                "例えば、別の合成入力でも同じ比較ができれば、といったことです。"],
            "future_aspiration_ja": "入力設計、評価実験、実データへの適用",
            "learning_candidates": ["比較手法の基礎知識の習得", "評価方法の基礎"],
            "source_map": [
                {"output": "①", "source_ids": ["profile.interest"]},
                {"output": "②", "source_ids": ["paper:AAAA1111"]},
                {"output": "③", "source_ids": [f"gap:{gap_id}"]},
                {"output": "future", "source_ids": [f"idea:{idea_id}"]}]}


def issue59_choices(email_id=ISSUE59_EMAIL_ID):
    return {"email_id": email_id, "first_choice": False,
            "signature_name": "試験 太郎", "learning": "比較手法の基礎知識の習得"}


def issue59_evidence_record(professor, item_key, *,
                            email=ISSUE59_EMAIL_ADDRESS):
    """One professor record exactly representable by the owner reconciler.

    Keep the pre-existing Issue-59 baseline on ``confirmed_cross_source``:
    the fixture now earns that verdict from a real official candidate plus one
    recent high-confidence correspondence record, instead of hand-authoring a
    schema-2 artifact that the owner checker would reject.
    """
    return {
        "professor": {"name": professor, "name_romaji": None},
        "official_emails": [{
            "email": email, "current_source": True,
            "provenance": [{"source_type": "official_professor_candidate",
                            "source": "issue59-fixture"}]}],
        "paper_correspondence": [{
            "email": email, "name": professor, "item_key": item_key, "doi": None,
            "paper_year": 2025, "channel": "correspondence", "confidence": "high",
            "identity_match": "direct", "recent": True,
            "current_email_evidence": False}],
        "identity": {"matched_verified_contacts": 1,
                     "unmatched_verified_contacts": [],
                     "ambiguous_unpaired_records_ignored": 0},
        "verdict": "confirmed_cross_source",
        "confirmed_emails": [email],
        "conflicting_paper_emails": [],
        "current_email": email,
        "evidence_status": {
            "official_candidates_unavailable": False,
            "professor_papers_unavailable": False,
            "paper_correspondence_unavailable": False,
            "signature_aliases_unavailable": False,
            "current_email_blocked_by": []},
    }


def issue59_projection_hash(value):
    """Hash the minimal owner projection used by this fixture.

    The source JSON below contains only fields consumed by
    professor-research/contact_evidence.py, so its owner projection is the
    value itself.  Canonical separators + sorted keys match the documented
    schema-2 fingerprint contract without copying the owner reconciler.
    """
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def issue59_source_fingerprint(source, path, professors_root, projection=None):
    path = Path(path)
    rel = path.relative_to(professors_root).as_posix()
    if projection is None:
        return {"source": source, "path": rel, "present": False,
                "sha256": None, "bytes": None}
    return {"source": source, "path": rel, "present": True,
            "sha256": issue59_projection_hash(projection),
            "bytes": len(path.read_bytes())}


def issue59_write_evidence(program_root, professor_dirs, stale_for=()):
    """Write an owner-contract-valid evidence handoff plus frozen snapshots.

    Unlike the source-state checker stub, this artifact is not synthetic
    readiness evidence: it follows professor-research's schema-2 handoff,
    including the persisted sources and non-empty fingerprint index that the
    real ``contact_evidence.py --check`` requires.  The stub is therefore
    limited to supplying the case-specific fresh/stale source-state report.
    """
    program_root = Path(program_root)
    professors_root = program_root / "教授研究"
    professor_dirs = {name: Path(path) for name, path in professor_dirs.items()}
    professors = list(professor_dirs)

    candidates = [
        {"name": name, "email": ISSUE59_EMAIL_ADDRESS, "source": "issue59-fixture"}
        for name in professors
    ]
    candidates_path = professors_root / "_professor_candidates.json"
    candidates_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8")

    paper_projections = []
    evidence_item_keys = {}
    correspondence = {}
    for index, (name, professor_dir) in enumerate(professor_dirs.items()):
        professor_dir.mkdir(parents=True, exist_ok=True)
        item_key = "AAAA1111" if index == 0 else f"ISS59{index:03d}"
        evidence_item_keys[name] = item_key
        papers = {
            "professor": {"name": name},
            "papers": [{"item_key": item_key, "year": 2025}],
        }
        papers_path = professor_dir / "papers.json"
        papers_path.write_text(
            json.dumps(papers, ensure_ascii=False, indent=1), encoding="utf-8")
        paper_projections.append((papers_path, papers))
        correspondence[item_key] = {
            "paper_year": 2025,
            "channel": "correspondence",
            "confidence": "high",
            "contacts": [{
                "name": name, "email": ISSUE59_EMAIL_ADDRESS,
                "channel": "correspondence", "confidence": "high",
            }],
        }

    correspondence_path = professors_root / "_corresp_cache.json"
    correspondence_path.write_text(
        json.dumps(correspondence, ensure_ascii=False, indent=1), encoding="utf-8")
    signature_path = professors_root / "_署名对照.json"
    fingerprints = [
        issue59_source_fingerprint(
            "professor_candidates", candidates_path, professors_root, candidates),
        issue59_source_fingerprint(
            "paper_correspondence", correspondence_path, professors_root,
            correspondence),
        issue59_source_fingerprint(
            "signature_book", signature_path, professors_root),
    ]
    fingerprints.extend(
        issue59_source_fingerprint(
            "papers_json", papers_path, professors_root, projection)
        for papers_path, projection in paper_projections)

    artifact = {
        "schema": 2, "kind": contact_state.CONTACT_EVIDENCE_KIND,
        "generated_at": contact_state.now_utc(),
        "recent_paper_years": 5, "current_year": int(contact_state.now_utc()[:4]),
        "scope": "workflow_evidence_not_send_time_authority",
        "sources": {
            "professor_candidates": "_professor_candidates.json",
            "paper_correspondence": "_corresp_cache.json",
            "signature_book": "_署名对照.json",
        },
        "degraded": False, "global_degraded": False, "source_errors": [],
        "source_fingerprints": {"algorithm": "sha256", "files": fingerprints},
        "professors": [
            issue59_evidence_record(name, evidence_item_keys[name])
            for name in professors
        ],
    }
    path = professors_root / contact_state.CONTACT_EVIDENCE_FILE
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
    snapshots = {}
    for name in professors:
        frozen = artifact
        if name in stale_for:
            frozen = json.loads(json.dumps(artifact, ensure_ascii=False))
            for record in frozen["professors"]:
                if record["professor"]["name"] == name:
                    record["official_emails"][0]["email"] = "moved@example.test"
                    record["current_email"] = "moved@example.test"
        snapshots[name] = contact_state.contact_evidence_snapshot(frozen, None, name)
    return snapshots


def install_issue59_checker(case, program_root, stale=None):
    """Certify fixture professors as source-state fresh, except ``stale``.

    The stub stands in for professor-research's ``contact_evidence.py`` and
    must live outside the program root, which holds user data only; the
    injected locator variable is restored when the case ends.
    """
    saved = os.environ.get(contact_state.UPSTREAM_SCRIPT_ENV)

    def restore():
        if saved is None:
            os.environ.pop(contact_state.UPSTREAM_SCRIPT_ENV, None)
        else:
            os.environ[contact_state.UPSTREAM_SCRIPT_ENV] = saved

    case.addCleanup(restore)
    holder = tempfile.TemporaryDirectory(prefix="issue59-checker-")
    case.addCleanup(holder.cleanup)
    script = Path(holder.name) / "skills" / "professor-collector" / "scripts"
    script = script / "contact_evidence.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    marker = Path(holder.name) / "rebuild-marker.txt"
    script.write_text(issue59_checker_stub(stale, marker), encoding="utf-8")
    os.environ[contact_state.UPSTREAM_SCRIPT_ENV] = str(script)
    return marker


def write_issue59_verify(program_root, professor_dir, professor, *, days_ago=1,
                         email_value=ISSUE59_EMAIL_ADDRESS):
    info = Path(program_root) / "info.json"
    boshu = Path(program_root) / "boshu_analysis.json"
    verify = {
        "professor": professor,
        "verified_at": (ISSUE59_VERIFIED_AT if days_ago == 1
                        else issue59_verified_at(days_ago)),
        "source_fingerprints": {
            "info_json": f"{info}:{int(info.stat().st_mtime)}",
            "boshu_analysis": f"{boshu}:{int(boshu.stat().st_mtime)}"},
        "items": {
            "email": {"verdict": "confirmed", "value": email_value, "sources": []},
            "roster": {"verdict": "confirmed", "value": "X分野/教授 @P.1", "sources": []},
            "season": {"verdict": "confirmed", "value": "春季 少数名", "sources": []},
            "header": {"verdict": "confirmed", "value": "", "sources": []},
            "subject_batch": {"verdict": "confirmed", "value": "", "sources": []},
            "schedule": {"verdict": "unverified", "value": None, "sources": []},
            "consent": {"verdict": "unverified", "value": None, "sources": []},
            "warnings": []}}
    path = Path(professor_dir) / "_contact_verify.json"
    path.write_text(json.dumps(verify, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def write_issue59_overview(program_root):
    """Seed the program aggregate with fixed bytes a targeted run must keep."""
    path = Path(program_root) / "教授研究" / contact_state.EMAIL_OVERVIEW
    path.write_text("# 套磁邮件总览\n\n> issue59 预置聚合表：定向运行不得改写\n",
                    encoding="utf-8")
    return path


def write_issue59_stale_overview(program_root):
    """A managed aggregate with a manual body edit after its recorded render sha."""
    body = ("# 套磁邮件总览\n\n> 2026-01-01T00:00:00Z ｜ 由 contact_state 渲染\n\n"
            "| 教授 | 方向（ja/zh） | 收件邮箱 | 核验 | 首封邮件 | 跟进邮件 | "
            "首封纯文本 | 跟进纯文本 |\n|---|---|---|---|---|---|---|---|\n")
    sha = contact_state.sha256_text(body)
    key = contact_state.EMAIL_OVERVIEW
    path = Path(program_root) / "教授研究" / key
    edited_body = body.replace("2026-01-01T00:00:00Z", "手工修改")
    path.write_text(contact_state.render_frontmatter(
        contact_state.sha256_obj({"projection": key, "body": sha}), sha) + edited_body,
        encoding="utf-8")
    (Path(program_root) / "教授研究" / contact_state.PROJECTIONS_FILE).write_text(
        json.dumps({"render": {key: {"sha256": "0" * 64}}}), encoding="utf-8")
    return path


def write_issue59_stage5_fixture(program_root, specs=(), *, extra_rows=(),
                                 overview=None, case=None):
    """Materialize the Stage 4 → Stage 5 handoff directly under ``program_root``.

    No Stage 2/3/4 runner is involved: each professor-local ``邮件输入.json``
    and each per-professor ``_contact_verify.json`` / ``套磁邮件状态.json``
    comes from this writer; the program aggregate is seeded only when requested.

    Each spec is a dict of ``professor`` / ``direction_id`` / ``idea_id`` /
    ``field`` / ``dir`` / ``verified``
    (``fresh`` | ``stale`` | ``missing`` | ``malformed``) /
    ``evidence`` (``none`` | ``fresh`` | ``stale``) / ``source_state``
    (``stale`` asks the injected checker to report that professor stale) /
    ``email_state``. ``overview`` seeds the program aggregate with ``"seed"``
    bytes or a conflicting managed render with ``"conflict"``.
    """
    program_root = Path(program_root)
    research = program_root / "教授研究"
    research.mkdir(parents=True, exist_ok=True)
    (program_root / "info.json").write_text(json.dumps({
        "university": "試験大学", "department": "試験研究科",
        "target": {"intake_year": 2027, "intake_term": "april"}}), encoding="utf-8")
    (program_root / "boshu_analysis.json").write_text(json.dumps({
        "exam_type": {"degree": "博士前期課程",
                      "selection_name": "春季 テスト選抜 合成工学専攻"}},
        ensure_ascii=False), encoding="utf-8")

    normalized = []
    for spec in (list(specs) or [{}]):
        spec = dict(spec)
        spec.setdefault("professor", ISSUE59_PROFESSOR)
        spec.setdefault("idea_id", ISSUE59_IDEA_ID)
        spec.setdefault("field", "X分野" if spec["professor"] == ISSUE59_PROFESSOR
                        else "Y分野")
        spec.setdefault("verified", "fresh")
        spec.setdefault("evidence", "fresh")
        spec.setdefault("dir", research / spec["field"] / spec["professor"])
        normalized.append(spec)

    wanted = list(dict.fromkeys(
        spec["professor"] for spec in normalized if spec["evidence"] != "none"))
    snapshots = {}
    checker_marker = None
    if wanted:
        if case is None:
            raise AssertionError(
                "issue59 fixture: an evidence snapshot needs a unittest case so "
                "PROFESSOR_CONTACT_EVIDENCE_SCRIPT is restored")
        checker_marker = install_issue59_checker(case, program_root, stale={
            spec["professor"]: ISSUE59_B_STALE_REASON for spec in normalized
            if spec.get("source_state") == "stale"})
        professor_dirs = {}
        for spec in normalized:
            if spec["evidence"] != "none":
                professor_dirs.setdefault(spec["professor"], Path(spec["dir"]))
        snapshots = issue59_write_evidence(
            program_root, professor_dirs,
            stale_for=[s["professor"] for s in normalized if s["evidence"] == "stale"])

    rows, dirs, verified_dirs = [], {}, {}
    for spec in normalized:
        professor_dir = Path(spec["dir"])
        row = issue59_email_row(
            spec["professor"], professor_dir,
            idea_id=spec["idea_id"],
            direction_id=spec.get("direction_id", ISSUE59_DIRECTION_ID),
            contact_evidence=snapshots.get(spec["professor"]))
        rows.append(row)
        dirs[spec["professor"]] = professor_dir
        professor_dir.mkdir(parents=True, exist_ok=True)
        if spec.get("email_state") is not None:
            payload = spec["email_state"]
            (professor_dir / contact_state.EMAIL_STATE).write_text(
                payload if isinstance(payload, str)
                else json.dumps(payload, ensure_ascii=False, indent=1),
                encoding="utf-8")
        if spec["verified"] == "missing":
            continue
        if spec["verified"] == "malformed":
            verified_dirs[spec["professor"]] = (
                professor_dir / contact_state.VERIFY_FILE)
            verified_dirs[spec["professor"]].write_text(
                ISSUE59_MALFORMED_JSON, encoding="utf-8")
            continue
        verified_dirs[spec["professor"]] = write_issue59_verify(
            program_root, professor_dir, spec["professor"],
            days_ago=1 if spec["verified"] == "fresh" else ISSUE59_STALE_DAYS)

    rows_by_professor = {}
    for row in rows:
        rows_by_professor.setdefault(row["professor"], []).append(row)
    primary_professor = ISSUE59_PROFESSOR if ISSUE59_PROFESSOR in dirs else next(iter(dirs))
    rows_by_professor.setdefault(primary_professor, []).extend(extra_rows)
    packs = {}
    for professor, owner_rows in rows_by_professor.items():
        professor_dir = dirs[professor]
        pack_path = professor_dir / contact_state.EMAIL_PACK
        pack_path.write_text(json.dumps({
            "schema": contact_state.STAGE4_LOCAL_SCHEMA,
            "kind": contact_state.EMAIL_PACK_KIND,
            "identity_version": contact_state.DIRECTION_IDENTITY_VERSION,
            "managed_by": contact_state.MANAGED_BY,
            "generated_at": contact_state.now_utc(),
            "program_root": str(program_root),
            "professor": professor,
            "professor_dir": str(professor_dir),
            "profile_fingerprint": None,
            "emails": owner_rows}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        packs[professor] = pack_path
    if overview == "conflict":
        write_issue59_stale_overview(program_root)
    elif overview == "seed":
        write_issue59_overview(program_root)
    return {"program_root": program_root,
            "pack": packs[primary_professor], "packs": packs, "rows": rows,
            "dirs": dirs, "verify": verified_dirs,
            "overview": (research / contact_state.EMAIL_OVERVIEW
                         if overview else None),
            "checker_marker": checker_marker,
            "email_ids": [row["email_id"] for row in rows],
            "gap_id": quote_id(ISSUE59_GAP_QUOTE)}


def issue59_local_pack_path(program_root, professor=ISSUE59_PROFESSOR):
    """Return the sole Stage-4 local pack that owns ``professor``."""
    research = Path(program_root) / "教授研究"
    matches = []
    for path in research.rglob(contact_state.EMAIL_PACK):
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if pack.get("professor") == professor:
            matches.append(path)
    if len(matches) != 1:
        raise AssertionError(
            f"expected one local email pack for {professor!r}, found {matches!r}")
    return matches[0]


ISSUE59_DEPENDENCY_VARIANTS = ("state", "verify", "clean", "overview-conflict")


def issue59_write_json(program_root, name, payload):
    path = Path(program_root) / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def issue59_write_results(program_root, name, email_ids, extra_rows=()):
    gap_id = quote_id(ISSUE59_GAP_QUOTE)
    rows = [issue59_result(gap_id, email_id=email_id,
                           idea_id=ISSUE59_IDEAS[email_id]) for email_id in email_ids]
    return issue59_write_json(program_root, name, rows + list(extra_rows))


def issue59_write_choices(program_root, name, email_ids, extra_rows=()):
    return issue59_write_json(
        program_root, name,
        [issue59_choices(email_id) for email_id in email_ids] + list(extra_rows))


def issue59_dependency_variant(program_root, variant, case):
    """Build T59-4 dependency shapes from scratch.

    ``state`` corrupts only B's 套磁邮件状态.json; ``verify`` corrupts only B's
    _contact_verify.json while its state still lists B's rendered files (the
    shape the pre-fix aggregate path read first); ``clean`` leaves both valid
    and seeds no program aggregate; ``overview-conflict`` leaves B valid and
    seeds only a managed aggregate projection conflict. Each variant is built
    in its own program root so every subcase changes one acceptance dimension.
    """
    program_root = Path(program_root)
    b_dir = program_root / "教授研究" / "Y分野" / ISSUE59_OTHER_PROFESSOR
    b_state = {"schema": 1, "kind": "email_state", "professor": ISSUE59_OTHER_PROFESSOR,
               "emails": {ISSUE59_OTHER_EMAIL_ID: {
                   "files": {"md": str(b_dir / "套磁邮件.md"),
                             "txt": str(b_dir / "套磁邮件.txt")},
                   "validation": {"result": "pass", "rounds": 1}}}}
    fixture = write_issue59_stage5_fixture(program_root, [
        {"professor": ISSUE59_PROFESSOR, "evidence": "fresh"},
        {"professor": ISSUE59_OTHER_PROFESSOR, "evidence": "fresh",
         "email_state": ISSUE59_MALFORMED_JSON if variant == "state" else b_state,
         "verified": "malformed" if variant == "verify" else "fresh"}],
        overview=("conflict" if variant == "overview-conflict"
                  else None if variant == "clean" else "seed"), case=case)
    if variant != "state":
        for name in ("套磁邮件.md", "套磁邮件.txt"):
            (b_dir / name).write_text("ISSUE59-B-RENDERED\n", encoding="utf-8")
    return {"fixture": fixture,
            "results": issue59_write_results(
                program_root, "issue59-dependency-raw.json", [ISSUE59_EMAIL_ID]),
            "choices": issue59_write_choices(
                program_root, "issue59-dependency-choices.json", [ISSUE59_EMAIL_ID]),
            "b_dir": b_dir,
            "b_state": b_dir / contact_state.EMAIL_STATE,
            "b_verify": b_dir / contact_state.VERIFY_FILE,
            "overview": fixture["overview"]}
