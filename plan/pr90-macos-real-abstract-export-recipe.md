# PR #90: macOS clean-install real abstract export

## Goal and current evidence

One acceptance item: a clean, complete APM consumer runs its installed Stage-2 router, which invokes the installed `zotero-read` helper and reads a real Zotero MCP instance, producing the matching nonempty normalized abstract JSON. One synthetic paper without PDF/OCR in an isolated library is sufficient. No model/eval, PDF/OCR, or complete professor-contact business run is required.

Product version: `professor-contact@36d74ae6761e92d70fb850c5f7dbddbf19de04e6`; exporter: `zotero-tools@7c39f03f0d6010e3e4ce8e51f7fc8ba761ef58d8`. A later documentation-only commit does not change these tested product revisions.

Existing evidence remains valid: 11 targeted router tests, `git diff --check`, real uv starting the exporter with `--help`, and router → uv → synthetic exporter. The subsequent cloud attempt fetched official Zotero/MCP assets and installed the two pinned skill subpackages, but the application did not reach MCP initialization. No real item/export assertion ran. That attempt is **unable to judge the real-export goal**, neither PASS nor product FAIL; it was not a complete workflow installation. This recipe is pending user execution.

## 1. Prepare a clean consumer (installation only)

Use your normal macOS terminal and HOME, retaining existing GitHub authentication and Nix/shell configuration. Required existing tools: APM, uv, Python **3.11 or newer** available as `python3` (the fixture uses `tomllib`), jq, curl, git, npm, and `/Applications/Zotero.app`. The commands below use APM's published `repo#ref` manifest installation syntax (also used by the cloud attempt, APM 0.33.0). Record the actual local APM version; do not change credentials, globally install `zotero-item-export`, clear HOME, or copy/symlink producer files into the consumer. Private transitive packages require your existing authorized GitHub access. A permission/install failure is a blocker: stop rather than silently substituting the narrower two-skill install.

Run the blocks in the same **bash** shell. Start it with `bash` if your terminal uses zsh. Run outside any producer repository. `cd -P` resolves macOS `/tmp` to its physical path and the directory deliberately contains spaces.

```bash
set -euo pipefail
RUN="$(mktemp -d /tmp/contact90-accept.XXXXXX)"
cd -P "$RUN"
export RUN="$PWD"
printf 'Acceptance run directory (retain this path): %s\n' "$RUN"
mkdir -p "$RUN/evidence" "$RUN/clean consumer" "$RUN/attempt-1"
cd -P "$RUN/clean consumer"
export CONSUMER="$PWD"
cat > apm.yml <<'YAML'
name: contact90-macos-acceptance
version: 0.0.0
description: Complete pinned consumer for Stage-2 real abstract export.
targets: [codex, opencode]
dependencies:
  apm:
    - ScholarWorkflow/professor-contact#36d74ae6761e92d70fb850c5f7dbddbf19de04e6
    - ScholarWorkflow/zotero-tools#7c39f03f0d6010e3e4ce8e51f7fc8ba761ef58d8
YAML
{ apm --version; uv --version; python3 --version; } > "$RUN/evidence/tool-versions.txt"
apm install --target codex,opencode 2>&1 | tee "$RUN/evidence/apm-install.log"
export CONTACT_SKILL="$CONSUMER/.agents/skills/professor-contact"
export ZOTERO_READ_SKILL="$CONSUMER/.agents/skills/zotero-read"
test -f "$CONTACT_SKILL/SKILL.md"
test -f "$CONTACT_SKILL/scripts/stage2_input_router.py"
test -f "$ZOTERO_READ_SKILL/SKILL.md"
test -f "$ZOTERO_READ_SKILL/scripts/zotero_item_export.py"
test -f "$ZOTERO_READ_SKILL/scripts/item_export_core.py"
test -f "$ZOTERO_READ_SKILL/scripts/new-session.sh"
printf 'consumer=%s\ncontact=%s\nzotero_read=%s\n' \
  "$CONSUMER" "$CONTACT_SKILL" "$ZOTERO_READ_SKILL" \
  > "$RUN/evidence/installed-paths.txt"
```

Retain `apm.lock.yaml` and the install log. Inspect the resolved commits for the two packages: they must equal the revisions above. These paths are the installed SKILL.md parents, not paths in `apm_modules` or a development checkout. If the installed layout differs or any file is missing, stop and report the installation result; do not repair it manually. The other transitive packages are recorded by this run's lockfile; this recipe does not add acceptance tests for them.

## 2. Prepare one isolated Zotero fixture

Use the existing shared fixture lifecycle, not a new profile launcher. The inspected fixture revision is `8cecafc694e4591dee47372f38903e5ac2b689fe`. Fill in **one value** below: the absolute path of your clean `skills-test-fixtures` checkout at that revision. If you already have a matching, exclusively assigned disposable fixture for this test, reuse its `fixture.env` and preparation record instead of starting another. Never source an unrelated run's environment or use the default personal-library endpoint. Do not stop/restart a personal Zotero process.

```bash
export FIXTURES="/REPLACE/absolute/path/to/skills-test-fixtures"
```

Or, if you have no matching checkout, use this block **instead of the assignment above** to obtain a separate fixture checkout without changing an existing one:

```bash
git clone https://github.com/RekiDunois/skills-test-fixtures.git "$RUN/skills-test-fixtures"
git -C "$RUN/skills-test-fixtures" checkout --detach 8cecafc694e4591dee47372f38903e5ac2b689fe
export FIXTURES="$RUN/skills-test-fixtures"
```

Then check the selected checkout:

```bash
test "$(git -C "$FIXTURES" rev-parse HEAD)" = 8cecafc694e4591dee47372f38903e5ac2b689fe
test -z "$(git -C "$FIXTURES" status --porcelain --untracked-files=all)"
```

If matching shared asset preparation is already valid, reuse it. Otherwise run the existing preparation entrypoint once (it also warms the shared Chrome MCP cache; no Chrome test is required here):

```bash
bash "$FIXTURES/scripts/prepare_shared_test_assets_macos.sh" \
  2>&1 | tee "$RUN/evidence/fixture-prepare.log"
```

Start an isolated fixture, or replace only the first assignment below with the absolute `fixture.env` of the already assigned disposable fixture. The starter owns port allocation, profile/data isolation and bounded readiness checks.

```bash
ZOTERO_FIXTURE_ENV="$(bash "$FIXTURES/scripts/start_zotero_test_fixture_macos.sh" \
  2> "$RUN/evidence/fixture-start.log")"
source "$ZOTERO_FIXTURE_ENV"
test "$FIXTURE_KIND" = zotero
test "$FIXTURE_RUN_ID" = "$ZOTERO_TEST_RUN_ID"
test "$SKILLS_TEST_FIXTURES_SHA" = 8cecafc694e4591dee47372f38903e5ac2b689fe
test "$SKILLS_TEST_FIXTURES_DIRTY" = no
printf 'fixture_env=%s\nfixture_evidence=%s\nendpoint=%s\n' \
  "$ZOTERO_FIXTURE_ENV" "$FIXTURE_EVIDENCE_FILE" "$ZOTERO_MCP_URL" \
  > "$RUN/evidence/fixture-location.txt"
```

Keep the supplied full `ZOTERO_MCP_URL` (already ends in `/mcp`). Do not replace it with port 23120. If startup fails, stop this attempt and retain the starter's reported run/log location. GUI activation is not needed for this MCP-only test; do not add GUI interactions to make an unready instance appear ready.

## 3. Create one known abstract in that disposable library

This preparation writes **one synthetic item only to the isolated fixture**; the acceptance export itself is read-only. The payload uses the existing Zotero MCP `write_item` contract. Do not run this block against a personal/production library. No attachments, collections, tags, or business state are created.

```bash
export EXPECTED_TITLE='Contact PR90 isolated abstract paper'
export EXPECTED_ABSTRACT='CONTACT90_SYNTHETIC_ABSTRACT: deterministic export of one paper without PDF or OCR.'
jq -n --arg title "$EXPECTED_TITLE" --arg abstract "$EXPECTED_ABSTRACT" \
  '{jsonrpc:"2.0",id:2,method:"tools/call",params:{name:"write_item",arguments:{
    action:"create",itemType:"journalArticle",fields:{title:$title,abstractNote:$abstract},
    creators:[{creatorType:"author",firstName:"Ada",lastName:"Example"}]}}}' \
  > "$RUN/seed-request.json"
SID="$(bash "$ZOTERO_READ_SKILL/scripts/new-session.sh")"
test -n "$SID"
curl --fail-with-body --silent --show-error --max-time 60 \
  -X POST "$ZOTERO_MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: $SID" --data-binary "@$RUN/seed-request.json" \
  > "$RUN/seed-response.txt"
# Parse either a JSON response or the MCP SSE data frame, then the text payload.
jq -Rs '. as $raw | try ($raw | fromjson) catch ($raw | split("\n") | map(select(startswith("data:")) |
  ltrimstr("data:") | fromjson) | map(select(has("result") or has("error"))) | last)' \
  "$RUN/seed-response.txt" > "$RUN/seed-rpc.json"
jq -e '(.error == null) and (.result.isError != true)' "$RUN/seed-rpc.json" >/dev/null
ITEM_KEY="$(jq -er '[.result.content[] | select(.type=="text") |
  .text | fromjson | (.data // .) | .itemKey |
  select(type=="string" and length>0)][0] // error("write_item returned no itemKey")' \
  "$RUN/seed-rpc.json")"
export ITEM_KEY
unset SID
```

The exporter creates its own session and reuses it across its batch. Reuse the running fixture service, not a manually injected session ID; no SID argument exists on the exporter. If seed creation is uncertain, inspect the retained response before repeating it; do not blindly create another item.

## 4. Run the installed router and check the business result

```bash
export OUT="$RUN/attempt-1"
jq -n --arg key "$ITEM_KEY" '[{item_key:$key}]' > "$OUT/papers.json"
cd -P "$CONSUMER"
python3 "$CONTACT_SKILL/scripts/stage2_input_router.py" \
  --zotero-read-skill-dir "$ZOTERO_READ_SKILL" \
  --papers "$OUT/papers.json" --output-dir "$OUT/exports" \
  > "$OUT/routes.json" 2> "$OUT/router.stderr"
jq -e --arg key "$ITEM_KEY" --arg path "$OUT/exports/$ITEM_KEY.json" '
  .status=="ok" and (.routes|length)==1 and
  (.routes[0] | .item_key==$key and .status=="ok" and
    .carrier=="abstract_json" and .level=="abstract" and
    .gap_only_allowed==false and .paper==$path and
    (has("abstract")|not) and (has("metadata")|not))
' "$OUT/routes.json" >/dev/null
jq -e --arg key "$ITEM_KEY" --arg title "$EXPECTED_TITLE" --arg abstract "$EXPECTED_ABSTRACT" '
  .schema==1 and .kind=="paper-analysis-input" and .source=="zotero" and
  .level=="abstract" and .item_key==$key and .metadata.title==$title and
  (.abstract|type)=="string" and (.abstract|length)>0 and .abstract==$abstract
' "$OUT/exports/$ITEM_KEY.json" >/dev/null
jq '{schema,kind,source,level,item_key,title:.metadata.title,
  abstract_length:(.abstract|length)}' "$OUT/exports/$ITEM_KEY.json" \
  > "$OUT/export-summary.json"
printf 'PASS: installed router exported the matching nonempty abstract. Evidence: %s\n' "$OUT"
```

The route input intentionally has no `pdf_path` or `ocr_path`; the synthetic library item has no attachments. `status=ok` alone is insufficient because an exporter can legitimately write an empty abstract; the checks require the exact known title/key/abstract. The router's process exit code is also insufficient: inspect its JSON status. Keep the installed exporter unchanged and do not substitute a fake exporter.

## 5. Record, stop and handle blockers

Report the two product revisions, APM/uv versions, consumer/fixture/run paths, install command/result, `routes.json`, `export-summary.json`, and PASS / business FAIL / unable to judge. Do not upload personal abstracts or full user-library responses. This synthetic item's text is not private, but a summary still suffices. Keep original failed attempts as well as any retry.

If installation, fixture startup or network access fails before the actual export, report **unable to judge**, with the specific blocker. A mismatching file after the real export is a business failure; do not replace the data or loosen assertions. Permit at most one export retry only after a transient connection/session fault is demonstrably resolved: reuse this installation, fixture and ITEM_KEY. Set a fresh output directory with the following two lines, then repeat section 4 **starting at `jq -n --arg key`**, skipping its `export OUT=...attempt-1` line. Keep all expected values unchanged. Do not reseed, retry a persistent blocker, or redo unrelated tests. If the seed/setup itself failed, stop and diagnose that step before a new formal attempt.

```bash
export OUT="$RUN/attempt-2"
mkdir -p "$OUT"
```

After saving the needed output and fixture logs outside the fixture run directory, stop **only a fixture you started for this recipe**, using its existing cleanup entrypoint. It removes that disposable profile/data/run directory and releases its lease. Leave an intentionally reused fixture to its owner; never use process-name kill commands.

```bash
# Only for a fixture started by this recipe, after retaining required logs:
bash "$FIXTURES/scripts/start_zotero_test_fixture_macos.sh" stop "$ZOTERO_FIXTURE_ENV"
```

## Sources and review status

- [APM 0.33.0 manifest installation](https://github.com/microsoft/apm/blob/v0.33.0/README.md)
- [Shared macOS fixture lifecycle](https://github.com/RekiDunois/skills-test-fixtures/blob/8cecafc694e4591dee47372f38903e5ac2b689fe/docs/runtime-fixture-architecture.md)
- [Pinned router](https://github.com/ScholarWorkflow/professor-contact/blob/36d74ae6761e92d70fb850c5f7dbddbf19de04e6/.apm/skills/professor-contact/scripts/stage2_input_router.py)
- [Pinned exporter contract](https://github.com/ScholarWorkflow/zotero-tools/blob/7c39f03f0d6010e3e4ce8e51f7fc8ba761ef58d8/.apm/skills/zotero-read/SKILL.md#L85-L98)
- [Existing synthetic write_item contract](https://github.com/ScholarWorkflow/zotero-tools/blob/7c39f03f0d6010e3e4ce8e51f7fc8ba761ef58d8/test/integration/mcp_seed.py)

Plan design / step review: independently reviewed read-only on 2026-10-16; no remaining blockers after clarifying Python 3.11+, preserving the seed parser exit status, and making retry output isolation explicit. Execution/result review: pending user execution; this document does not claim a real-export pass.
