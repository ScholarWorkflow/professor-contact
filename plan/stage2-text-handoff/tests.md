# Stage 2 text-only handoff — test plan and recipe

- Requirement revision: user 2026-10-25 lightweight upload/unified PDF flow/two plans; latest clarification: hash original PDF in place, no new PDF copies.
- Test plan revision TP3 (candidate), paired with EP3.1. Proposed review status: pending. Gate1/Gate2/Gate3 not yet reviewed; no result claimed.
- Baseline: professor-contact `856f396e3ac3083600919f094fd63908bc99a4e2` (PR140).
- Authority: [Test Engineer](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253), [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d).

## Required checks — acceptance ceiling

| ID | Goal/input | Expected | Sufficient check |
|---|---|---|---|
| T1 | PDF prepared text + abstract job | Page-tagged text/context/evidence in ZIP; no PDF/image copies in upload/staging/handoff dir; original unchanged; local record has original path only locally; source/facts expectations preserved and text hash bound | Existing unittest ZIP/JSON/file assertions with known fixture bytes |
| T2 | Older prepare lacking source_pages; valid/stale fulltext/page caches | Same-install helper supplies missing text; valid cache reused, stale ignored; physical pages retained, no hidden OCR/cache prerequisite | Focused orchestration tests plus one real installed-helper CLI export for fallback interface |
| T3 | Required/untrusted pages versus isolated empty page with trusted text | Required local preparation suppresses upload but leaves usable local lease; wait describes need; isolated allowed blank page retains marker/limitation without blanket OCR | Targeted unittest input/state/lease assertions, no vision service |
| T4 | New result/new local-source record; missing/changed source or edited transport; old embedded bundle | Valid matching input finalizes facts/future-work against original PDF; missing/changed source/text fails before installation; legacy import unchanged | Existing import fixture adapted to new local source path plus representative byte/path changes; legacy fixture |
| T5 | Both runtime callers + web instructions | Wait/continue and resume use current new paths correctly; no PDF fallback or webpage OCR of absent images; missing visual evidence disclosed | Read changed sections plus directly applicable existing contract assertions |

No full Stage0–5 runs, installation matrix, candidate algorithm tests, engine certification, boundary combinations, performance ratio gate or new evaluator. Compression size is descriptive only.

## Recipe

1. Run in isolated cloud producer checkout; record actual commit and Python version. Use a fresh `/tmp` directory below. Existing dependency/interpreter/installed helper set is reused; no install or user state access.
2. Add direct tests in `test_stage2_chatgpt_handoff_text.py`; adapt directly affected existing fixtures for the new default source-local contract. Existing legacy fixtures retain embedded PDF behavior. Use unittest/tempfile/zipfile/JSON assertions. No second verification framework.
3. Execute focused tests:
   `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage2_chatgpt_handoff_text.py' -v`.
   For T4/T5 reuse directly affected existing tests, record their exact selectors before running; do not default to all-repo regression.
4. T2 real interface export uses this exact preparation (creates a disposable source PDF, not a copy of user material):

```bash
RUN=$(mktemp -d /tmp/contact-text-handoff.XXXXXX)
export RUN
PY=/workspace/shared/paper-sentence-fix/.venv/bin/python
PA=/workspace/shared/contact90-cloud-live/consumer-full-attempt-preserved/.agents/skills/paper-analysis
AGENT=/workspace/shared/contact90-cloud-live/consumer-full-attempt-preserved/.codex/agents/paper-analysis.toml
CONTACT="$PWD/.apm/skills/professor-contact/scripts/stage2_chatgpt_handoff.py"
"$PY" --version
# Check only this recipe's existing required resources; absence is unable-to-judge.
test -f "$PA/scripts/future_work.py" && test -f "$PA/scripts/pdf_runtime.py" && test -f "$AGENT"
"$PY" - <<'PY'
import os
from pathlib import Path
import pymupdf
r = Path(os.environ['RUN']); (r/'Professor').mkdir()
doc = pymupdf.open(); page = doc.new_page()
page.insert_textbox(pymupdf.Rect(50,50,540,750),
    '\n'.join(['A study of compact handoff transport and reproducible paper evidence.'] * 15), fontsize=10)
doc.save(r/'source.pdf'); doc.close()
PY
"$PY" "$PA/scripts/future_work.py" prepare "$RUN/source.pdf" --debug-dir "$RUN/prepared" > "$RUN/prepare-summary.json"
"$PY" - <<'PY'
import json, os
from pathlib import Path
r=Path(os.environ['RUN'])
job={'item_key':'TEXT1','carrier':'pdf','level':'fulltext',
     'input_path':str(r/'source.pdf'),'analysis_relpath':'论文分析/A/Text.md',
     'research_direction':{},'research_direction_fp':'fixture',
     'future_work_prepare':str(r/'prepared/prepare.json'),
     'future_work_candidates':str(r/'prepared/candidates.json')}
(r/'jobs.json').write_text(json.dumps({'schema':1,'jobs':[job]}))
PY
CONTACT_PAPER_PYTHON="$PY" "$PY" "$CONTACT" build \
  --professor-dir "$RUN/Professor" --jobs "$RUN/jobs.json" \
  --paper-analysis-skill-dir "$PA" --paper-analysis-agent "$AGENT" > "$RUN/build.json"
jq '{status,upload_ready,bundle_path,local_manifest_path,handoff_id,text_preparation}' "$RUN/build.json"
```

Read the returned ZIP text/manifest directly (zipfile + JSON or unzip/jq); verify known original sentence and physical page marker, source input_sha256 equals original source, no PDF/image or local absolute path in archive, and local record points to `$RUN/source.pdf`. The producer test assertions cover those semantics; this one real command establishes the installed helper interface. Do not repeat real exports for every cache branch or invoke models/OCR/API.

5. T5 read changed Codex/OpenCode Step4.5 and generated instructions. Run `git diff --check`. If a new module changes existing shard inventory, add it to `plan/test-grouping/shards.json` and run `python scripts/check_test_shards.py` only to keep required tests runnable.
6. Save actual commands, target results, first failures and relevant output under RUN. Commit only concise non-sensitive results under this plan directory. No user PDFs/raw temporary files in Git.

## Failure/retry and review

- Assertion failures retain first output; diagnose and correct product or propose recipe correction with impact, then rerun affected targets only. Do not weaken expected behavior to pass.
- Missing resources/external dependency failure is unable-to-judge for affected check. No installation or unchanged repeated attempts. Corrected path/availability permits one retry with reason; changed inputs/expectations require recipe revision.
- No model/external service is required. No automatic global safety/config changes.
- Reuse unaffected PR140 instruction-snapshot results. Documentation SHA alone triggers no rerun.
- Independent reviewer confirms Gate1/2 before execution, Gate3 afterward; author records observations without self-APPROVED or self-review PASS.

TP3 supersedes TP2: T1/T4 check original-source lookup with zero copied PDFs; T3 preserves original missing-page policy and continue lease; real CLI commands now explicit. No expanded test matrix.
