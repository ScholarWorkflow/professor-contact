#!/usr/bin/env bash
set -o pipefail

readonly uv_cache_dir='/private/tmp/issue66-uv-cache'
readonly plan_revision='issue-66-test-plan-r19-clarification-r7-2026-10-07'
readonly runner_revision='issue-66-local-candidate-runner-r21-2026-10-07'

usage() {
  printf '用法：%s local\n' "$0" >&2
  printf 'Gate2 尚未批准；正式评测被禁用。本脚本只运行本地候选检查。\n' >&2
  exit 64
}

stop() {
  local message="$1"
  printf 'CASE_NOT_STARTED\t%s\n' "$message" > "$evidence_dir/outcome.txt"
  printf '拒绝继续：%s\n证据目录：%s\n' "$message" "$evidence_dir" >&2
  exit 64
}

[[ "$#" -eq 1 && "$1" == 'local' ]] || usage

script_dir="$(cd -- "$(dirname -- "$BASH_SOURCE")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
tmp_root='/tmp'
if [[ -n "$TMPDIR" ]]; then
  tmp_root="$TMPDIR"
fi
if [[ "$tmp_root" != '/' ]]; then
  tmp_root="${tmp_root%/}"
fi
umask 077

if ! evidence_dir="$(mktemp -d "$tmp_root/issue66-gate2-candidate.XXXXXXXX")"; then
  printf '无法在临时目录创建唯一证据目录。\n' >&2
  exit 64
fi
if ! mkdir -p "$evidence_dir/commands"; then
  printf '无法初始化证据目录：%s\n' "$evidence_dir" >&2
  exit 64
fi

readonly evidence_dir
readonly repo_root
readonly script_dir
export EVIDENCE_DIR="$evidence_dir"
export UV_CACHE_DIR="$uv_cache_dir"

commands_tsv="$evidence_dir/commands.tsv"
suites_tsv="$evidence_dir/suites.tsv"
printf 'name\texit_code\tcommand\tstdout\tstderr\n' > "$commands_tsv"
printf 'suite\tresult\tactual_test_count\texit_code\tactual_items\tactual_failures\tdetail\n' > "$suites_tsv"
printf 'mktemp -d %s/issue66-gate2-candidate.XXXXXXXX\n' "$tmp_root" \
  > "$evidence_dir/commands/bootstrap-mktemp.command"
printf '%s\n' "$evidence_dir" > "$evidence_dir/commands/bootstrap-mktemp.stdout"
: > "$evidence_dir/commands/bootstrap-mktemp.stderr"
printf 'bootstrap-mktemp\t0\t%s\t%s\t%s\n' \
  "$(<"$evidence_dir/commands/bootstrap-mktemp.command")" \
  "$evidence_dir/commands/bootstrap-mktemp.stdout" \
  "$evidence_dir/commands/bootstrap-mktemp.stderr" >> "$commands_tsv"
printf 'mkdir -p %s/commands\n' "$evidence_dir" \
  > "$evidence_dir/commands/bootstrap-mkdir.command"
: > "$evidence_dir/commands/bootstrap-mkdir.stdout"
: > "$evidence_dir/commands/bootstrap-mkdir.stderr"
printf 'bootstrap-mkdir\t0\t%s\t%s\t%s\n' \
  "$(<"$evidence_dir/commands/bootstrap-mkdir.command")" \
  "$evidence_dir/commands/bootstrap-mkdir.stdout" \
  "$evidence_dir/commands/bootstrap-mkdir.stderr" >> "$commands_tsv"

capture() {
  local name="$1"
  shift
  local stdout_path="$evidence_dir/commands/$name.stdout"
  local stderr_path="$evidence_dir/commands/$name.stderr"
  local command_path="$evidence_dir/commands/$name.command"
  local escaped=''
  local escaped_sample_ledger=''
  local arg=''
  local rc=0

  for arg in "$@"; do
    printf -v arg '%q' "$arg"
    if [[ -n "$escaped" ]]; then
      escaped="$escaped "
    fi
    escaped="$escaped$arg"
  done
  if [[ "$1" == 'uv' ]]; then
    escaped="UV_CACHE_DIR=$UV_CACHE_DIR $escaped"
  fi
  if [[ -n "${ISSUE66_SAMPLE_LEDGER:-}" ]]; then
    printf -v escaped_sample_ledger '%q' "$ISSUE66_SAMPLE_LEDGER"
    escaped="ISSUE66_SAMPLE_LEDGER=$escaped_sample_ledger $escaped"
  fi
  printf '%s\n' "$escaped" > "$command_path"
  "$@" > "$stdout_path" 2> "$stderr_path"
  rc=$?
  printf '%s\t%d\t%s\t%s\t%s\n' \
    "$name" "$rc" "$escaped" "$stdout_path" "$stderr_path" >> "$commands_tsv"
  return "$rc"
}

capture_required() {
  local name="$1"
  shift
  local rc=0
  capture "$name" "$@"
  rc=$?
  [[ "$rc" -eq 0 ]] || stop "命令 $name 失败，退出码 $rc。"
}

capture_required invocation-directory pwd -P
invocation_directory="$(<"$evidence_dir/commands/invocation-directory.stdout")"
if ! cd -- "$repo_root"; then
  stop "无法切换到仓库根目录：$repo_root"
fi

run_suite() {
  local name="$1" pattern="$2"
  local report="$evidence_dir/suite-$1.json"
  local rc=0 result='INVALID_TEST_EXECUTION' actual_test_count='NOT_PARSED'
  local failures='[]' items='[]' failure_count='NOT_PARSED' evidence_validity='INVALID'
  local owner='product'
  case "$name" in
    judge|execution_wiring|structured_result) owner='test_program' ;;
  esac
  capture "suite-$name" uv run --no-project python -B \
    .apm/skills/professor-contact/tests/runtime/issue66_suite_result.py \
    --directory .apm/skills/professor-contact/tests --pattern "$pattern" --report "$report"
  rc=$?
  if jq -e --argjson rc "$rc" '
      def nonempty: type == "string" and length > 0;
      .schema == "issue66-suite-result-v1"
      and (.exit_code | type == "number") and .exit_code == $rc
      and (.tests_run | type == "number" and . >= 0)
      and (.tests | type == "array") and .tests_run == (.tests | length)
      and (.failures | type == "number" and . >= 0)
      and (.errors | type == "number" and . >= 0)
      and (.skipped | type == "number" and . >= 0)
      and (.classification == "PASS" or .classification == "PRODUCT_FAIL"
        or .classification == "INVALID_TEST_EXECUTION")
      and all(.tests[];
        (.test_id | nonempty)
        and (.ordinal | type == "number" and . > 0)
        and (.status == "ok" or .status == "failure" or .status == "error"
          or .status == "skipped" or .status == "expected_failure"
          or .status == "unexpected_success")
        and (.events | type == "array"))
      and ([.tests[].ordinal] | length == (unique | length))
      and ([.tests[].ordinal] | sort) == [range(1; .tests_run + 1)]
      and ([.tests[].test_id] | length == (unique | length))
    ' "$report" > "$evidence_dir/commands/suite-$name-report-validation.stdout" \
      2> "$evidence_dir/commands/suite-$name-report-validation.stderr"; then
    result="$(jq -r --arg owner "$owner" -f \
      .apm/skills/professor-contact/tests/runtime/issue66_suite_classify.jq "$report")"
    actual_test_count="$(jq -r '.tests_run' "$report")"
    failure_count="$(jq -r '[.tests[] | select(.status != "ok")] | length' "$report")"
    failures="$(jq -c '[.tests[] | select(.status != "ok") | {ordinal,test_id,status,events}]' "$report")"
    items="$(jq -c '[.tests[] | {ordinal,test_id,status,events}]' "$report")"
    evidence_validity='VALID'
  fi
  printf '%s\t%s\t%s\t%d\t%s\t%s\t%s\n' \
    "$name" "$result" "$actual_test_count" "$rc" \
    "$items" "$failures" "结构化记录：$failure_count 个失败条目。" >> "$suites_tsv"
  jq -n --arg suite "$name" --arg result "$result" --argjson exit_code "$rc" \
    --arg owner "$owner" --arg validity "$evidence_validity" \
    --argjson actual_test_count "$(if [[ "$actual_test_count" == 'NOT_PARSED' ]]; then printf 'null'; else printf '%s' "$actual_test_count"; fi)" \
    --argjson items "$items" --argjson failures "$failures" \
    --arg status_source "suite-$name.json#tests.status" \
    --arg raw_source "suite-$name.json#tests.events" \
    '{suite:$suite,result:$result,exit_code:$exit_code,actual_test_count:$actual_test_count,
      items:$items,owner:$owner,
      evidence_validity:$validity,structured_status_source:$status_source,
      raw_event_source:$raw_source,failures:$failures}' >> "$evidence_dir/suites.jsonl"
  printf '%s：%s（%s 项，退出码 %d）\n' "$name" "$result" "$actual_test_count" "$rc"
}
validate_judge_sample_ledger() {
  capture "judge-ledger-assertion-diagnostics" jq -s '
    def fact_value($record; $fact):
      ([$record.actual.result.facts[]? | select(.fact == $fact) | .verdict]) as $values
      | if ($values | length) == 1 then $values[0] else null end;
    def assertion_fact_id($record; $subject):
      if $subject == "attribution[\u0027verdict\u0027]" then "F-attribution"
      elif $subject == "observed[\u0027F-attribution\u0027]" then "F-attribution"
      elif $subject == "observed[\u0027F-routing-verifier\u0027]" then "F-routing-verifier"
      elif $subject == "facts(verdict)[fact]"
        and $record.test_id == "test_issue66_runtime_judge.FoldedEvidenceTests.test_required_install_sample_and_snapshot_evidence_cannot_be_omitted"
        and $record.evidence_ref.run_ordinal >= 1 and $record.evidence_ref.run_ordinal <= 5 then
        ["F-install", "F-fixture", "F-pre-snapshot", "F-post-snapshot", "F-routing-verifier"][$record.evidence_ref.run_ordinal - 1]
      elif ($subject | test("^facts\\(verdict\\)\\[\u0027F-[A-Za-z0-9-]+\u0027\\]$")) then
        ($subject | capture("^facts\\(verdict\\)\\[\u0027(?<fact>F-[A-Za-z0-9-]+)\u0027\\]$").fact)
      else null end;
    def assertion_actual($record; $assertion):
      if $assertion.result_selector.kind == "path" then
        $record.actual.result | getpath($assertion.result_selector.path)
      elif $assertion.result_selector.kind == "fact" then
        fact_value($record; $assertion.result_selector.fact)
      elif $assertion.subject == "verdict[\u0027classification\u0027]" then $record.actual.result.classification
      else assertion_fact_id($record; $assertion.subject) as $fact
        | if $fact == null then null else fact_value($record; $fact) end
      end;
    def assertion_matches($record; $assertion):
      (if $assertion.operator == "equals" then $assertion.expected_value == $assertion.observed_value
        elif $assertion.operator == "not_equals" then $assertion.expected_value != $assertion.observed_value
        else false end)
      and (if $assertion.verdict_related == true then
        assertion_actual($record; $assertion) as $actual
        | $actual != null and $assertion.observed_value == $actual
        else true end);
    [ .[] as $record
      | $record.expected.assertions[]? as $assertion
      | assertion_actual($record; $assertion) as $actual
      | select(assertion_matches($record; $assertion) | not)
      | {sample_id: $record.sample_id, test_id: $record.test_id,
         run_ordinal: $record.evidence_ref.run_ordinal,
         subject: $assertion.subject, expected: $assertion.expected_value,
         observed: $assertion.observed_value, actual_result_value: $actual,
         source: $assertion.source}
    ]
  ' "$EVIDENCE_DIR/judge-samples.jsonl"
  local diagnostics_rc=$?
  if [[ "$diagnostics_rc" -ne 0 ]]; then
    return 1
  fi
  capture "judge-ledger-validate" jq -e -s '
    def digest: type == "string" and test("^[0-9a-f]{64}$");
    def nonempty: type == "string" and length > 0;
    def fact_value($record; $fact):
      ([$record.actual.result.facts[]? | select(.fact == $fact) | .verdict]) as $values
      | if ($values | length) == 1 then $values[0] else null end;
    def assertion_fact_id($record; $subject):
      if $subject == "attribution[\u0027verdict\u0027]" then "F-attribution"
      elif $subject == "observed[\u0027F-attribution\u0027]" then "F-attribution"
      elif $subject == "observed[\u0027F-routing-verifier\u0027]" then "F-routing-verifier"
      elif $subject == "facts(verdict)[fact]"
        and $record.test_id == "test_issue66_runtime_judge.FoldedEvidenceTests.test_required_install_sample_and_snapshot_evidence_cannot_be_omitted"
        and $record.evidence_ref.run_ordinal >= 1 and $record.evidence_ref.run_ordinal <= 5 then
        ["F-install", "F-fixture", "F-pre-snapshot", "F-post-snapshot", "F-routing-verifier"][$record.evidence_ref.run_ordinal - 1]
      elif ($subject | test("^facts\\(verdict\\)\\[\u0027F-[A-Za-z0-9-]+\u0027\\]$")) then
        ($subject | capture("^facts\\(verdict\\)\\[\u0027(?<fact>F-[A-Za-z0-9-]+)\u0027\\]$").fact)
      else null end;
    def assertion_actual($record; $assertion):
      if $assertion.result_selector.kind == "path" then
        $record.actual.result | getpath($assertion.result_selector.path)
      elif $assertion.result_selector.kind == "fact" then
        fact_value($record; $assertion.result_selector.fact)
      elif $assertion.subject == "verdict[\u0027classification\u0027]" then $record.actual.result.classification
      else assertion_fact_id($record; $assertion.subject) as $fact
        | if $fact == null then null else fact_value($record; $fact) end
      end;
    def assertion_matches($record; $assertion):
      (if $assertion.operator == "equals" then $assertion.expected_value == $assertion.observed_value
        elif $assertion.operator == "not_equals" then $assertion.expected_value != $assertion.observed_value
        else false end)
      and (if $assertion.verdict_related == true then
        assertion_actual($record; $assertion) as $actual
        | $actual != null and $assertion.observed_value == $actual
        else true end);
    [
      "three_completion_paths",
      "source_handoff_values",
      "formal_relations",
      "raw_messages",
      "file_permissions",
      "order_and_stops",
      "refusal_side_effects",
      "read_reuse",
      "evidence_channels"
    ] as $allowed_families
    | all(.[];
        . as $record
        | .schema_version == "issue66.sample-ledger.v1"
        and (.sample_id | nonempty)
        and (.test_id | nonempty)
        and (.sample_id == (.test_id + "#run-" + (.evidence_ref.run_ordinal | tostring)))
        and (.sample_family | type == "array" and length > 0
          and all(.[]; . as $family | $allowed_families | index($family) != null))
        and (.expected | type == "object"
          and (.status == "available" or .status == "partial")
          and (.classification_status == "asserted" or .classification_status == "not_asserted")
          and (.facts_status == "asserted" or .facts_status == "partial" or .facts_status == "not_asserted")
          and (.assertions | type == "array")
          and ((.status == "unavailable") or
            (.assertions | length > 0 and all(.[];
              has("subject") and has("expected_expression") and has("expected_value")
              and has("observed_value")
              and (.operator == "equals" or .operator == "not_equals")
              and (.source | type == "object" and (.file | nonempty)
                and (.line | type == "number" and . > 0))
              and (.verdict_related | type == "boolean")
            )))
        )
        and (if .expected.classification_status == "asserted"
          then .expected.status == "available"
            and (.expected.classification | type == "string" and length > 0)
            and .expected.classification == .actual.result.classification
          else .expected.status == "partial"
            and (.expected.facts_status == "asserted" or .expected.facts_status == "partial")
            and ((.expected.facts | type == "object" and length > 0)
              or (.expected.fact_constraints | type == "array" and length > 0))
            and any(.expected.assertions[]?;
              .verdict_related == true and
                (.result_selector.kind == "fact" or .subject == "facts(verdict)[fact]"
                  or (.subject | test("^facts\\(verdict\\)\\[\u0027F-[A-Za-z0-9-]+\u0027\\]$"))))
          end)
        and (.actual | type == "object" and (.outcome | nonempty)
          and (.result | type == "object")
          and .outcome == .result.classification)
        and all($record.expected.assertions[]?;
          . as $assertion | assertion_matches($record; $assertion))
        and (.judge_sha256 | digest)
        and (.evidence_digest | digest)
        and (.evidence_ref as $ref
          | ($ref | type == "object"
            and .kind == "synthetic_fixture"
            and (.source_file | nonempty)
            and (.run_call_line | type == "number" and . > 0)
            and (.run_ordinal | type == "number" and . > 0)
            and (.event_count | type == "number" and . >= 0)
            and (.event_refs | type == "array")
            and (if .event_count == 0 then (.event_refs | length) == 0
              else (.event_refs | length) > 0 end))
          and ($ref.raw_app_server_events | type == "array"
            and length == $ref.event_count)
          and all($ref.event_refs[];
            . as $event_ref
            | ($ref.raw_app_server_events[$event_ref.array_index]) as $event
            | ($event.message // {}) as $message
            | ($message.params // {}) as $params
            | (if ($params.item | type) == "object"
               then $params.item else {} end) as $item
            | ($event_ref.seq == ($event.seq // ($event_ref.array_index + 1)))
              and ($event_ref.method == $message.method)
              and ($event_ref.thread_id == $params.threadId)
              and ($event_ref.turn_id == $params.turnId)
              and ($event_ref.item_type == $item.type)
              and ($event_ref.item_id == $item.id)
              and ($event_ref.call_id == $item.call_id))
        )
      )
      and ([.[].sample_id] | length == (unique | length))
  ' "$EVIDENCE_DIR/judge-samples.jsonl"
}

write_sample_records() {
  local sample_id=''
  local independent_expected=''
  local suite=''
  local test_name=''
  local program_path=''
  local source_pointer=''
  local source_detail=''
  local requested_oracle_type=''
  local plan_family=''
  local call_ordinal='1'
  local oracle_type='judge-verdict'
  local runtime_test_id=''
  local runtime_sample_id=''
  local runtime_family=''
  local expected_class_status=''
  local expected_class=''
  local expected_json=''
  local actual_outcome=''
  local actual_result=''
  local judge_sha=''
  local evidence_digest=''
  local event_count=''
  local event_refs=''
  local event_pointer=''
  local raw_sample_pointer=''
  local mapped_line=''
  local map_rc=0
  local expected_class_from_plan=''
  local stderr_path=''
  local test_status='NOT_FOUND'
  local test_status_count=0
  local actual_observation='GAP_NO_SINGLE_TEST_STATUS'
  local sample_row_count=0
  local sample_tsv_rows=0
  local sample_tsv_column_count=0
  local tsv_line=''
  local tsv_tabs=''
  local -a header_fields=()
  local -a row_fields=()
  local sample_ledger_valid='true'
  local source_file=''
  local source_line=''
  local source_line_count=0
  local family=''
  local seen_sample_ids='|'

  printf 'sample_id\toracle_type\tindependent_expected\tobserved\tplan_sample_family\tjudge_sample_family\tjudge_sample_id\tjudge_test_id\tjudge_expected_classification_status\tjudge_expected_classification\tjudge_expected_json\tactual_outcome\tactual_result_json\tjudge_sha256\tevidence_digest\tevent_count\tevent_refs_json\tprogram_path\ttest_status\tsource_pointer\tsource_detail\traw_evidence_pointer\n' \
    > "$evidence_dir/samples.tsv"
  IFS=$'\t' read -r -a header_fields < "$evidence_dir/samples.tsv"
  sample_tsv_column_count=${#header_fields[@]}
  validate_judge_sample_ledger || sample_ledger_valid='false'

  while IFS='|' read -r sample_id independent_expected suite test_name \
    program_path source_pointer source_detail call_ordinal requested_oracle_type; do
    [[ -z "$sample_id" ]] && continue
    if [[ "$seen_sample_ids" == *"|$sample_id|"* ]]; then
      sample_ledger_valid='false'
    fi
    seen_sample_ids+="$sample_id|"
    family="${sample_id:6:1}"
    call_ordinal="${call_ordinal:-1}"
    requested_oracle_type="${requested_oracle_type:-judge-verdict}"
    [[ "$family" =~ ^[A-I]$ ]] || sample_ledger_valid='false'
    stderr_path="$evidence_dir/commands/suite-$suite.stderr"
    test_status_count="$(jq --arg method "$test_name" '[.tests[] | select(.method == $method)] | length' "$evidence_dir/suite-$suite.json")"
    test_status="$(jq -r --arg method "$test_name" '[.tests[] | select(.method == $method)] | if length == 1 then .[0].status else "NOT_FOUND" end' "$evidence_dir/suite-$suite.json")"
    if [[ "$test_status_count" -eq 1 && "$test_status" == 'ok' ]]; then
      actual_observation="assertion-matched:${independent_expected}"
    elif [[ "$test_status_count" -eq 1 ]]; then
      actual_observation="assertion-not-passed:$test_status"
      sample_ledger_valid='false'
    else
      actual_observation="GAP_TEST_STATUS_COUNT:$test_status_count"
      sample_ledger_valid='false'
    fi

    case "$family" in
      A) plan_family='three_completion_paths' ;;
      B) plan_family='source_handoff_values' ;;
      C) plan_family='formal_relations' ;;
      D) plan_family='raw_messages' ;;
      E) plan_family='file_permissions' ;;
      F) plan_family='order_and_stops' ;;
      G) plan_family='refusal_side_effects' ;;
      H) plan_family='read_reuse' ;;
      I) plan_family='evidence_channels' ;;
    esac

    oracle_type='judge-verdict'
    runtime_test_id='NOT_MAPPED'
    runtime_sample_id='NOT_MAPPED'
    runtime_family='NOT_MAPPED'
    expected_class_status='NOT_MAPPED'
    expected_class='NOT_MAPPED'
    expected_json='NOT_MAPPED'
    actual_outcome='NOT_MAPPED'
    actual_result='NOT_MAPPED'
    judge_sha='NOT_APPLICABLE'
    evidence_digest='NOT_APPLICABLE'
    event_count='NOT_APPLICABLE'
    event_refs='NOT_APPLICABLE'
    event_pointer='NOT_APPLICABLE'
    raw_sample_pointer='NOT_APPLICABLE'
    if [[ "$requested_oracle_type" == 'direct-assertion' ]]; then
      oracle_type='direct-assertion'
      runtime_family='NOT_APPLICABLE'
      runtime_sample_id='NOT_APPLICABLE'
      runtime_test_id='NOT_APPLICABLE'
      expected_class_status='not_applicable'
      expected_class='not_applicable'
      event_pointer='NOT_APPLICABLE'
      event_count='NOT_APPLICABLE'
      event_refs='NOT_APPLICABLE'
      actual_outcome='assertion-matched'
      capture "sample-map-$sample_id" jq -cnr \
        --arg predicate "$independent_expected" \
        --arg test_status "$test_status" \
        '[{oracle_type:"direct-assertion",independent_predicate:$predicate},
          {observation:"assertion-matched",test_status:$test_status}]
         | map(tojson)
         | join("\u001f")'
      if [[ "$?" -eq 0 ]]; then
        IFS=$'\037' read -r expected_json actual_result \
          < "$evidence_dir/commands/sample-map-$sample_id.stdout"
      else
        sample_ledger_valid='false'
        actual_result='{}'
      fi
      raw_sample_pointer="suite-$suite.json#tests.method=$test_name;commands/suite-$suite.stderr;test-source=$source_pointer"
    else
      capture "sample-map-$sample_id" jq -e -s -r \
        --arg suffix ".$test_name" --argjson ordinal "$call_ordinal" '
        [.[] | select((.test_id | endswith($suffix))
          and .evidence_ref.run_ordinal == $ordinal)]
        | if length != 1 then error("sample mapping must resolve to one judge call")
          else .[0] as $record
          | [$record.test_id, $record.sample_id,
             ($record.sample_family | join(",")),
             $record.expected.classification_status,
             ($record.expected.classification // "NOT_ASSERTED"),
             ($record.expected | tojson),
             $record.actual.outcome, ($record.actual.result | tojson),
             $record.judge_sha256, $record.evidence_digest,
             ($record.evidence_ref.event_count | tostring),
             ($record.evidence_ref.event_refs | tojson),
             ($record.evidence_ref.source_file + ":" +
              ($record.evidence_ref.run_call_line | tostring) + "#run-" +
              ($record.evidence_ref.run_ordinal | tostring))]
           | join("\u001f")
           end
        ' "$EVIDENCE_DIR/judge-samples.jsonl"
      map_rc=$?
      mapped_line="$(<"$evidence_dir/commands/sample-map-$sample_id.stdout")"
      if [[ "$map_rc" -eq 0 ]]; then
        IFS=$'\037' read -r runtime_test_id runtime_sample_id runtime_family \
          expected_class_status expected_class expected_json actual_outcome actual_result \
          judge_sha evidence_digest event_count event_refs event_pointer \
          <<< "$mapped_line"
        actual_observation="judge-verdict:$actual_outcome"
        if [[ "$expected_class_status" == 'asserted' ]]; then
          expected_class_from_plan="${independent_expected#classification=}"
          expected_class_from_plan="${expected_class_from_plan%%;*}"
          if [[ "$independent_expected" != classification=* \
            || "$expected_class" != "$expected_class_from_plan" ]]; then
            sample_ledger_valid='false'
          fi
        elif [[ "$expected_class_status" == 'not_asserted' ]]; then
          expected_class='NOT_ASSERTED'
        else
          sample_ledger_valid='false'
        fi
        if [[ ! "$judge_sha" =~ ^[0-9a-f]{64}$ \
          || ! "$evidence_digest" =~ ^[0-9a-f]{64}$ \
          || "$actual_outcome" == 'NOT_MAPPED' ]]; then
          sample_ledger_valid='false'
        fi
        raw_sample_pointer="commands/suite-$suite.stderr#$test_name;judge-samples.jsonl#$runtime_sample_id;fixture=$event_pointer;raw_app_server_events=judge-samples.jsonl#$runtime_sample_id.evidence_ref.raw_app_server_events;event_index_refs=$event_refs"
      else
        sample_ledger_valid='false'
        actual_observation='GAP_NO_UNIQUE_JUDGE_SAMPLE'
        actual_result='{}'
        raw_sample_pointer="commands/suite-$suite.stderr#$test_name;judge-samples.jsonl#unmapped"
      fi
    fi

    source_file="${source_pointer%%:*}"
    capture "source-pointer-$sample_id" rg -n \
      "^[[:space:]]*def ${test_name}\\(" "$repo_root/$source_file"
    map_rc=$?
    if [[ "$map_rc" -eq 0 ]]; then
      source_line_count=0
      while IFS= read -r line || [[ -n "$line" ]]; do
        source_line_count=$((source_line_count + 1))
        source_line="${line%%:*}"
      done < "$evidence_dir/commands/source-pointer-$sample_id.stdout"
      if [[ "$source_line_count" -eq 1 && "$source_line" =~ ^[0-9]+$ ]]; then
        source_pointer="$source_file:$source_line"
      else
        sample_ledger_valid='false'
        source_pointer="$source_file:GAP_MULTIPLE_SOURCE_LINES"
      fi
    else
      sample_ledger_valid='false'
      source_pointer="$source_file:GAP_SOURCE_LINE_NOT_FOUND"
    fi
    if [[ ! -f "$repo_root/$source_file" || ! -s "$stderr_path" ]]; then
      sample_ledger_valid='false'
    fi
    sample_row_count=$((sample_row_count + 1))

    row_fields=(
      "$sample_id" "$oracle_type" "$independent_expected" "$actual_observation"
      "$plan_family" "$runtime_family" "$runtime_sample_id" "$runtime_test_id"
      "$expected_class_status" "$expected_class" "$expected_json" "$actual_outcome"
      "$actual_result" "$judge_sha" "$evidence_digest" "$event_count" "$event_refs"
      "$program_path" "$test_status"
      "$source_pointer" "$source_detail" "$raw_sample_pointer"
    )
    printf '%s' "${row_fields[0]}" >> "$evidence_dir/samples.tsv"
    for ((field_index = 1; field_index < ${#row_fields[@]}; field_index++)); do
      printf '\t%s' "${row_fields[$field_index]}" >> "$evidence_dir/samples.tsv"
    done
    printf '\n' >> "$evidence_dir/samples.tsv"
  done <<'SAMPLE_RECORDS'
R19-5-A1|classification=PASS;branch:correction_round=NOT TESTED|judge|test_one_round_pass|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:599|one-round pass; natural correction branch recorded NOT TESTED
R19-5-A2|classification=PASS|judge|test_corrected_two_round_pass|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:615|legal corrected two-round fixture
R19-5-A3|classification=PASS|judge|test_two_round_exhaustion_is_a_legal_pass|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:621|legal two-round exhaustion fixture
R19-5-B1|classification=PASS|judge|test_consumption_uses_actual_capture_return_path_and_digest|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:898|capture return path and digest bound to consumption
R19-5-B2|classification=FAIL|judge|test_credential_return_bound_to_another_professor_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:989|other-professor credential
R19-5-B3|classification=FAIL|judge|test_source_metadata_drift_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:971|credential source metadata drift
R19-5-B4|classification=FAIL|judge|test_missing_first_commit_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1024|missing first commit
R19-5-B5|classification=FAIL|judge|test_handoff_value_drift_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1567|handoff value drift
R19-5-B6|classification=FAIL|judge|test_prepare_return_for_another_round_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1583|round binding
R19-5-B7|classification=FAIL;fact:F-credential-chain=fail|judge|test_committed_profile_fingerprint_must_match_capture|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|committed state profile fingerprint differs from captured source fingerprint
R19-5-C1|classification=PASS|judge|test_one_round_pass|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:599|formal root delegation and routing chain
R19-5-C2|classification=FAIL|judge|test_named_root_call_with_confirmed_zero_children_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|named root call with confirmed zero children
R19-5-C3|classification=FAIL|judge|test_nested_foreign_relation_is_product_failure|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:709|nested foreign relation
R19-5-C4|classification=INVALID_TEST_EXECUTION|judge|test_conflicting_formal_owners_for_child_are_invalid|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:761|conflicting formal owners
R19-5-C5|classification=FAIL|judge|test_extra_off_root_formal_relation_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|additional off-root formal relation
R19-5-D1|classification=PASS|judge|test_legal_whitespace_message_passes|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:627|legal whitespace message bytes
R19-5-D2|classification=FAIL|judge|test_root_reconstruction_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1088|root reconstructs child output
R19-5-D3|classification=FAIL|judge|test_second_business_message_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1101|second business message
R19-5-D4|classification=FAIL|judge|test_complete_run_with_no_validator_production_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1108|missing validator production in complete run
R19-5-D5|digest-and-state-from-first-buffer|validation_handoff|test_record_parses_the_same_buffer_that_was_digest_checked|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_validation_handoff.py|replace valid source after digest check; digest and recorded state use first buffer||direct-assertion
R19-5-D6|add_diff_preserves_original_utf8_bytes|judge|test_file_change_add_diff_preserves_utf8_and_line_endings|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|Unicode, CRLF, LF, and trailing-newline bytes preserved||direct-assertion
R19-5-D7|app_server_file_change_shape_lifecycle_delete_and_move_target|judge|test_file_change_protocol_shape_bytes_lifecycle_delete_and_move_target|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|Started/completed pairing and success, required string diff, add/delete/update, move_path scope, unsupported-kind and unsupported-field evidence gaps; Add cannot prove exclusive creation||direct-assertion
R19-5-E1|classification=PASS|judge|test_compound_legal_read_and_single_exclusive_output_write_passes|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1327|legal read and exclusive output write
R19-5-E2|classification=FAIL|judge|test_python_command_with_multiple_write_targets_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1256|multiple write targets
R19-5-E3|classification=FAIL|judge|test_same_byte_write_then_restore_still_fails_write_scope|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1270|same-byte rewrite and restore
R19-5-E4|classification=FAIL|judge|test_overwrite_existing_candidate_source_fails_write_scope|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1285|overwrite an existing candidate source
R19-5-E5|classification=FAIL|judge|test_outside_output_write_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|write to a single non-designated target
R19-5-E6|classification=INVALID_TEST_EXECUTION;fact:F-validator-write-scope=gap|judge|test_pure_unknown_command_is_an_evidence_gap|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|unrecognized command; write scope remains a gap
R19-5-E7|classification=INVALID_TEST_EXECUTION;fact:F-validator-write-scope=gap|judge|test_pure_unknown_command_is_an_evidence_gap|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|write appears only inside an uncalled function; evidence is inconclusive|2
R19-5-E8|classification=INVALID_TEST_EXECUTION;fact:F-validator-write-scope=gap|judge|test_pure_unknown_command_is_an_evidence_gap|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|write appears only in an unreachable branch; evidence is inconclusive|3
R19-5-F1|classification=BLOCKED|judge|test_machine_failure_prefix_blocks|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:661|valid external failure prefix
R19-5-F2|classification=FAIL|judge|test_correction_dispatch_between_record_start_and_completion_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1388|correction starts before record completion
R19-5-F3|classification=FAIL|judge|test_machine_failure_prefix_does_not_hide_prior_product_failure|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:686|prior product failure survives later machine failure
R19-5-F4|classification=FAIL|judge|test_rebuild_started_before_terminal_record_completed_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1481|rebuild before terminal record completion
R19-5-F5|classification=INVALID_TEST_EXECUTION;fact:F-rebuild=gap|judge|test_rebuild_without_completion_is_an_evidence_gap|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1526|rebuild lacks completion evidence
R19-5-F6|classification=FAIL|judge|test_terminal_round_bookkeeping_fails|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|incorrect terminal round count
R19-5-F7|classification=FAIL|judge|test_unrecognized_failure_text_does_not_hide_zero_child_failure|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|unrecognized machine failure text cannot hide confirmed zero-child failure
R19-5-F8|classification=FAIL;fact:F-stop-order=fail|judge|test_failed_prepare_write_and_record_stop_dependent_actions|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|failed prepare followed by validator dispatch|1
R19-5-F9|classification=FAIL;fact:F-stop-order=fail|judge|test_failed_prepare_write_and_record_stop_dependent_actions|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|failed validator write followed by save|2
R19-5-F10|classification=FAIL;fact:F-stop-order=fail|judge|test_failed_prepare_write_and_record_stop_dependent_actions|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|failed record followed by rebuild|3
R19-5-F11|classification=FAIL;fact:F-rebuild=fail;fact:F-attribution=invalid|judge|test_machine_failure_prefix_does_not_hide_prior_product_failure|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|independent early rebuild failure survives conflicting formal owners|2
R19-5-F12|classification=FAIL;fact:F-stop-order=pass;fact:F-credential-chain=fail|judge|test_internal_generator_failure_reports_once_and_stops|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal plan failure, one error report, no dependent action|1
R19-5-F13|classification=FAIL;fact:F-stop-order=pass;fact:F-credential-chain=fail|judge|test_internal_generator_failure_reports_once_and_stops|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal finalize failure, one error report, no dependent action|2
R19-5-F14|classification=FAIL;fact:F-stop-order=fail;fact:F-credential-chain=fail|judge|test_internal_generator_failure_then_dependent_action_fails_stop|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal plan failure followed by dependent prepare|1
R19-5-F15|classification=FAIL;fact:F-stop-order=fail;fact:F-credential-chain=fail|judge|test_internal_generator_failure_then_dependent_action_fails_stop|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal finalize failure followed by dependent prepare|2
R19-5-F16|classification=FAIL;fact:F-stop-order=fail|judge|test_internal_generator_failure_does_not_allow_second_report|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal failure followed by duplicate error report|1
R19-5-F17|classification=FAIL;fact:F-stop-order=fail|judge|test_internal_generator_failure_does_not_allow_success_report|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|internal failure followed by success report|1
R19-5-G1|artifact_set=unchanged_on_refusal|credential|test_credential_rejection_preserves_the_full_committed_artifact_set|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py|credential rejection snapshot||direct-assertion
R19-5-G2|artifact_set=unchanged_on_refusal|validation_handoff|test_prepare_save_and_record_refusals_preserve_the_same_artifact_set|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_validation_handoff.py|prepare save and record refusal snapshots||direct-assertion
R19-5-H1|read_set=matches_independent_expected|credential|test_exact_result_read_set_rejects_an_extra_open|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py|real open positive control and out-of-set negative control||direct-assertion
R19-5-H2|extra_open=detected_without_byte_change|credential|test_exact_result_read_set_rejects_an_extra_open|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py|sentinel unchanged after observed open||direct-assertion
R19-5-H3|dir_C_validator_record=preserved|credential|test_named_group_is_replaced_and_sibling_group_is_kept|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py|unmodified dir_C result preserved||direct-assertion
R19-5-H4|cleared_dir_C_record=detected|credential|test_named_group_is_replaced_and_sibling_group_is_kept|.apm/skills/professor-contact/scripts/contact_state.py|.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py|negative control deletes dir_C validator record||direct-assertion
R19-6-I1|classification=INVALID_TEST_EXECUTION|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|subTest missing=install|1
R19-6-I2|classification=INVALID_TEST_EXECUTION|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|subTest missing=fixture|2
R19-6-I3|classification=INVALID_TEST_EXECUTION|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|subTest missing=pre|3
R19-6-I4|classification=INVALID_TEST_EXECUTION|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|subTest missing=post|4
R19-6-I5|classification=INVALID_TEST_EXECUTION|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|subTest missing=routing|5
R19-6-I6|classification=INVALID_TEST_EXECUTION|judge|test_truncated_record_output_is_invalid|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1539|truncated evidence output
R19-6-I7|classification=INVALID_TEST_EXECUTION|judge|test_unsupported_message_shape_is_invalid|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1555|unsupported message shape
R19-6-I8|classification=INVALID_TEST_EXECUTION|judge|test_non_monotonic_event_seq_invalidates_validator_evidence|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1666|non-monotonic event sequence
R19-6-I9|classification=INVALID_TEST_EXECUTION|judge|test_mismatched_call_id_cannot_bind_validator_command_completion|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py:1693|mismatched call id
R19-6-I10|classification=INVALID_TEST_EXECUTION|judge|test_mixed_evidence_set_ids_are_invalid|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|mixed evidence-set identifiers
R19-6-I11|missing_response=INVALID_TEST_EXECUTION;F-test-program=invalid;F-evidence-set=invalid|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|top-level eval response file is missing||direct-assertion
R19-6-I12|truncated_response=INVALID_TEST_EXECUTION;F-test-program=invalid;F-evidence-set=invalid|judge|test_required_install_sample_and_snapshot_evidence_cannot_be_omitted|.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py|.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py|top-level eval response file is truncated||direct-assertion
SAMPLE_RECORDS

  while IFS= read -r tsv_line || [[ -n "$tsv_line" ]]; do
    sample_tsv_rows=$((sample_tsv_rows + 1))
    tsv_tabs="${tsv_line//[^$'\t']/}"
    if [[ "${#tsv_tabs}" -ne $((sample_tsv_column_count - 1)) || "$tsv_line" == *$'\t\t'* \
      || "$tsv_line" == $'\t'* || "$tsv_line" == *$'\t' ]]; then
      sample_ledger_valid='false'
    fi
  done < "$evidence_dir/samples.tsv"
  if [[ "$sample_tsv_rows" -ne $((sample_row_count + 1)) ]]; then
    sample_ledger_valid='false'
  fi
  if [[ "$sample_ledger_valid" == 'true' ]]; then
    printf 'sample_ledger_status=VALID_JUDGE_AND_DIRECT_ASSERTION_RECORDS\n' >> "$evidence_dir/metadata.txt"
    return 0
  fi
  printf 'sample_ledger_status=INVALID_TEST_EXECUTION\n' >> "$evidence_dir/metadata.txt"
  return 1
}

capture_required uv-version uv --version
capture_required bash-version bash --version
capture_required jq-version jq --version
capture_required rg-version rg --version
capture_required git-version git --version
capture codex-version codex --version
capture opencode-version opencode --version
capture shasum-version shasum --version
capture_required shasum-probe shasum -a 256 /dev/null
capture_required bash-syntax bash -n "$script_dir/issue-66-run.sh"
capture shellcheck-probe bash -c 'command -v shellcheck'
shellcheck_probe_rc=$?
shellcheck_status='NOT_INSTALLED'
if [[ "$shellcheck_probe_rc" -eq 0 ]]; then
  shellcheck_status='PASS'
  capture_required shellcheck-version shellcheck --version
  capture_required shellcheck-script shellcheck "$script_dir/issue-66-run.sh"
fi
capture_required python-version uv run --no-project python --version
capture_required platform uname -a
capture repository-root git -C "$repo_root" rev-parse --show-toplevel
capture repository-origin git -C "$repo_root" remote get-url origin
capture repository-status git -C "$repo_root" status --short --branch
capture source-commit git -C "$repo_root" rev-parse HEAD

{
  printf 'repository_root=%s\n' "$repo_root"
  printf 'repository_origin=%s\n' "$(<"$evidence_dir/commands/repository-origin.stdout")"
  printf 'worktree=%s\n' "$repo_root"
  printf 'invocation_directory=%s\n' "$invocation_directory"
  printf 'source_commit=%s\n' "$(<"$evidence_dir/commands/source-commit.stdout")"
  printf 'source_worktree_status=%s\n' "$(<"$evidence_dir/commands/repository-status.stdout")"
  printf 'source_worktree_status_is_informational=true\n'
  printf 'product_source=当前仓库源码树；提交与工作树状态见来源记录\n'
  printf 'product_source_commit=%s\n' "$(<"$evidence_dir/commands/source-commit.stdout")"
  printf 'test_source=当前仓库测试树；提交与工作树状态见来源记录\n'
  printf 'test_source_commit=%s\n' "$(<"$evidence_dir/commands/source-commit.stdout")"
  printf 'fixture_source=NOT_USED_BY_LOCAL_DETERMINISTIC_TESTS\n'
  printf 'adapter_source=NOT_USED_BY_LOCAL_DETERMINISTIC_TESTS\n'
  printf 'uv_cache_dir=%s\n' "$UV_CACHE_DIR"
  printf 'plan_revision=%s\n' "$plan_revision"
  printf 'runner_revision=%s\n' "$runner_revision"
  printf 'uv_version=%s\n' "$(<"$evidence_dir/commands/uv-version.stdout")"
  printf 'python_version=%s\n' "$(<"$evidence_dir/commands/python-version.stdout")"
  printf 'bash_version=%s\n' "$(<"$evidence_dir/commands/bash-version.stdout")"
  printf 'jq_version=%s\n' "$(<"$evidence_dir/commands/jq-version.stdout")"
  printf 'rg_version=%s\n' "$(<"$evidence_dir/commands/rg-version.stdout")"
  printf 'git_version=%s\n' "$(<"$evidence_dir/commands/git-version.stdout")"
  printf 'shasum_version=%s\n' "$(<"$evidence_dir/commands/shasum-version.stdout")"
  printf 'codex_version=%s\n' "$(<"$evidence_dir/commands/codex-version.stdout")"
  printf 'opencode_version=%s\n' "$(<"$evidence_dir/commands/opencode-version.stdout")"
  printf 'shellcheck_status=%s\n' "$shellcheck_status"
  printf 'python_project_install=DISABLED_BY_UV_NO_PROJECT\n'
  printf 'local_model=NOT_USED_BY_DETERMINISTIC_TESTS\n'
  printf 'local_thinking_level=NOT_USED_BY_DETERMINISTIC_TESTS\n'
  printf 'local_sandbox=NOT_APPLICABLE\n'
  printf 'local_install_command=NOT_APPLICABLE\n'
  printf 'suite_command=uv run --no-project python -B issue66_suite_result.py\n'
  printf 'formal_eval_mode=NOT_AVAILABLE_IN_LOCAL_MODE\n'
  printf 'formal_eval_request=NOT_SENT_BY_LOCAL_MODE\n'
} > "$evidence_dir/metadata.txt"

printf '源码提交记录：%s\n' "$(<"$evidence_dir/commands/source-commit.stdout")"
printf '证据目录：%s\n' "$evidence_dir"

export ISSUE66_SAMPLE_LEDGER="$EVIDENCE_DIR/judge-samples.jsonl"
: > "$ISSUE66_SAMPLE_LEDGER"
run_suite judge test_issue66_runtime_judge.py
unset ISSUE66_SAMPLE_LEDGER
run_suite execution_wiring test_issue66_execution_wiring.py
run_suite structured_result test_issue66_suite_result.py
run_suite credential test_issue66_invocation_credential.py
run_suite local_state test_issue66_stage3_local_state.py
run_suite validation_handoff test_issue66_validation_handoff.py
run_suite agent_contract test_stage3_idea_generator_agent_contract.py

combination_check_rc=0
while IFS= read -r method; do
  combination_dir="$evidence_dir/candidate-combinations/$method"
  capture "candidate-combination-$method" jq -e \
    --slurpfile expected "$combination_dir/independent-expected.json" \
    --slurpfile raw "$combination_dir/raw-suite.json" \
    --slurpfile input "$combination_dir/input.json" '
      .schema == "issue66-candidate-result-v1"
      and .overall == $expected[0].overall
      and .evidence_validity == $expected[0].evidence_validity
      and (.local_product_failures | length) == $expected[0].local_product_failure_count
      and .runner_execution == "COMPLETE"
      and .runner_execution_meaning == "仅表示运行器已执行完全部步骤；不表示证据有效、候选通过或正式验收通过"
      and $input[0].suites[0].result == $raw[0].classification
      and $input[0].suites[0].failures == [$raw[0].tests[] | select(.status != "ok")]
    ' "$combination_dir/actual.json" || combination_check_rc=1
done <<'CANDIDATE_COMBINATIONS'
test_valid_candidate_with_independent_product_failure
test_invalid_ledger_keeps_independent_product_failure
test_invalid_material_cannot_attribute_product_failure
test_valid_candidate_all_checks_pass
CANDIDATE_COMBINATIONS

sample_ledger_rc=0
write_sample_records || sample_ledger_rc=$?

ledger_validity='VALID'
[[ "$sample_ledger_rc" -eq 0 && "$combination_check_rc" -eq 0 ]] || ledger_validity='INVALID'
jq -n --arg ledger_validity "$ledger_validity" \
  --argjson sample_ledger_exit_code "$sample_ledger_rc" \
  --argjson combination_check_exit_code "$combination_check_rc" \
  --slurpfile suites "$evidence_dir/suites.jsonl" \
  '{candidate:{validity:"RECORDED",source:"metadata.txt;commands/"},
    ledger:{validity:$ledger_validity,source:"samples.tsv;judge-samples.jsonl;candidate-combinations/",
            sample_ledger_exit_code:$sample_ledger_exit_code,
            combination_check_exit_code:$combination_check_exit_code},suites:$suites}' \
  > "$evidence_dir/candidate-summary-input.json"
capture_required candidate-overall jq -f \
  .apm/skills/professor-contact/tests/runtime/issue66_candidate_classify.jq \
  "$evidence_dir/candidate-summary-input.json"
cp "$evidence_dir/commands/candidate-overall.stdout" "$evidence_dir/candidate-result.json"
overall="$(jq -r '.overall' "$evidence_dir/candidate-result.json")"
exit_code="$(jq -r '.exit_code' "$evidence_dir/candidate-result.json")"
printf 'candidate_verdict=%s\nrunner_execution=COMPLETE\n' "$overall" > "$evidence_dir/outcome.txt"
printf 'runner_execution_meaning=仅表示运行器已执行完全部步骤；不表示证据有效、候选通过或正式验收通过\n' >> "$evidence_dir/outcome.txt"
printf 'candidate_verdict=%s\n' "$overall" >> "$evidence_dir/metadata.txt"
printf 'evidence_directory=%s\n' "$evidence_dir" >> "$evidence_dir/metadata.txt"
printf '运行完成：%s；退出码 %d；证据目录：%s\n' "$overall" "$exit_code" "$evidence_dir"
exit "$exit_code"
