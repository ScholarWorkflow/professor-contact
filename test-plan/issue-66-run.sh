#!/usr/bin/env bash
set -o pipefail

readonly product_target_sha='112a16cb6aa6c34d9abb5a018436a1735308ad83'
readonly fixture_tree_sha='c738fa2f8bcbb16cd99d741332d5f59b062b6357'
readonly adapter_pin='skills-test-fixtures/codex-eval-adapter@16'
readonly repository_slug='ScholarWorkflow/professor-contact'
readonly uv_cache_dir='/private/tmp/issue66-uv-cache'

usage() {
  printf '用法：%s local\n' "$0" >&2
  printf '本脚本只运行本地候选检查，不含正式评测入口。\n' >&2
  exit 64
}

stop() {
  local message="$1"
  printf 'PRECHECK_FAILED\t%s\n' "$message" > "$evidence_dir/outcome.txt"
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
umask 077

if ! evidence_dir="$(mktemp -d "$tmp_root/issue66-gate2-candidate.XXXXXXXX" 2>/dev/null)"; then
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
export UV_CACHE_DIR="$uv_cache_dir"

commands_tsv="$evidence_dir/commands.tsv"
suites_tsv="$evidence_dir/suites.tsv"
printf 'name\texit_code\tcommand\tstdout\tstderr\n' > "$commands_tsv"
printf 'suite\tresult\ttest_count\texit_code\tdetail\n' > "$suites_tsv"

capture() {
  local name="$1"
  shift
  local stdout_path="$evidence_dir/commands/$name.stdout"
  local stderr_path="$evidence_dir/commands/$name.stderr"
  local command_path="$evidence_dir/commands/$name.command"
  local escaped=''
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

candidate_files='.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py
.apm/skills/professor-contact/tests/test_issue66_runtime_judge.py
.apm/skills/professor-contact/tests/test_issue66_invocation_credential.py
.apm/skills/professor-contact/tests/test_issue66_validation_handoff.py
.apm/skills/professor-contact/tests/test_issue66_stage3_local_state.py
test-plan/issue-66.md
test-plan/issue-66-run.sh'

allowed_change() {
  local candidate="$1"
  local path=''
  while IFS= read -r path; do
    [[ "$candidate" == "$path" ]] && return 0
  done <<< "$candidate_files"
  [[ "$candidate" == .tmp_scripts/* ]]
}

verify_changed_paths() {
  local changed=''
  capture_required changed-tracked-files git -C "$repo_root" diff HEAD --name-only
  capture_required changed-untracked-files git -C "$repo_root" ls-files --others --exclude-standard

  while IFS= read -r changed; do
    [[ -z "$changed" ]] && continue
    allowed_change "$changed" || stop "候选范围外的已跟踪变更：$changed"
  done < "$evidence_dir/commands/changed-tracked-files.stdout"
  while IFS= read -r changed; do
    [[ -z "$changed" ]] && continue
    allowed_change "$changed" || stop "候选范围外的未跟踪文件：$changed"
  done < "$evidence_dir/commands/changed-untracked-files.stdout"
}

write_candidate_manifest() {
  local phase="$1"
  local manifest_path="$2"
  local index=0
  local file=''
  local hash_output=''
  local file_hash=''
  : > "$manifest_path"

  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    [[ -f "$repo_root/$file" ]] || stop "候选文件缺失：$file"
    index=$((index + 1))
    capture_required "hash-$phase-$index" shasum -a 256 "$repo_root/$file"
    hash_output="$(<"$evidence_dir/commands/hash-$phase-$index.stdout")"
    read -r file_hash _ <<< "$hash_output"
    [[ "$file_hash" =~ ^[0-9a-f]{64}$ ]] || stop "无法解析候选文件摘要：$file"
    printf '%s  %s\n' "$file_hash" "$file" >> "$manifest_path"
  done <<< "$candidate_files"
}

run_suite() {
  local name="$1"
  local pattern="$2"
  local test_count="$3"
  local expected="$4"
  local failure_marker="$5"
  local expected_failure_count="$6"
  local rc=0
  local combined=''
  local result='INVALID_TEST_EXECUTION'
  local detail='实际输出未满足预期条目数、退出码或已知失败特征。'

  capture "suite-$name" uv run --python 3.14 python -B -m unittest discover \
    -s .apm/skills/professor-contact/tests -p "$pattern" -v
  rc=$?
  combined="$(<"$evidence_dir/commands/suite-$name.stdout")"$'\n'"$(<"$evidence_dir/commands/suite-$name.stderr")"

  if [[ "$expected" == 'PASS' ]]; then
    if [[ "$rc" -eq 0 && "$combined" == *"Ran $test_count tests"* && "$combined" == *'OK'* ]]; then
      result='PASS'
      detail='整份测试文件按预期通过。'
    fi
  elif [[ "$expected" == 'PRODUCT_FAIL' ]]; then
    if [[ "$rc" -eq 1 \
      && "$combined" == *"Ran $test_count tests"* \
      && "$combined" == *"FAILED (failures=$expected_failure_count)"* \
      && "$combined" == *"$failure_marker"* ]]; then
      result='PRODUCT_FAIL'
      detail="复现已知产品行为失败：$failure_marker"
    fi
  fi

  printf '%s\t%s\t%s\t%d\t%s\n' \
    "$name" "$result" "$test_count" "$rc" "$detail" >> "$suites_tsv"
  printf '%s：%s（%s 项，退出码 %d）\n' "$name" "$result" "$test_count" "$rc"
}

capture_required uv-version uv --version
capture_required python-version uv run --python 3.14 python --version
capture_required platform uname -a
capture_required repository-root git -C "$repo_root" rev-parse --show-toplevel
capture_required repository-origin git -C "$repo_root" remote get-url origin
capture_required test-commit-sha git -C "$repo_root" rev-parse HEAD
capture_required product-target-resolve git -C "$repo_root" rev-parse "$product_target_sha^{commit}"
capture_required product-target-ancestor git -C "$repo_root" merge-base --is-ancestor \
  "$product_target_sha" "$(<"$evidence_dir/commands/test-commit-sha.stdout")"
capture_required diff-check git -C "$repo_root" diff HEAD --check

resolved_root="$(<"$evidence_dir/commands/repository-root.stdout")"
origin_url="$(<"$evidence_dir/commands/repository-origin.stdout")"
test_commit_sha="$(<"$evidence_dir/commands/test-commit-sha.stdout")"
resolved_product_sha="$(<"$evidence_dir/commands/product-target-resolve.stdout")"
[[ "$resolved_root" == "$repo_root" ]] || stop '脚本目录与 Git 工作树根目录不一致。'
[[ "$origin_url" == *"$repository_slug"* ]] || stop 'origin 未指向 ScholarWorkflow/professor-contact。'
[[ "$resolved_product_sha" == "$product_target_sha" ]] || stop '无法解析固定产品目标提交。'
[[ "$test_commit_sha" =~ ^[0-9a-f]{40}$ ]] || stop '无法记录当前测试提交 SHA。'
verify_changed_paths

record_text="$(<"$script_dir/issue-66.md")"
[[ "$record_text" == *"$fixture_tree_sha"* ]] || stop '候选记录未固定共享夹具提交。'
[[ "$record_text" == *"$adapter_pin"* ]] || stop '候选记录未固定适配器约定。'
[[ "$record_text" == *'Gate2 待批准'* ]] || stop '候选记录没有保留 Gate2 待批准状态。'
[[ "$record_text" == *'未运行'* ]] || stop '候选记录没有明确正式评测未运行状态。'

candidate_manifest="$evidence_dir/candidate-files.sha256"
write_candidate_manifest before "$candidate_manifest"
capture_required candidate-summary shasum -a 256 "$candidate_manifest"
candidate_summary=''
read -r candidate_summary _ < "$evidence_dir/commands/candidate-summary.stdout"
[[ "$candidate_summary" =~ ^[0-9a-f]{64}$ ]] || stop '无法计算本地候选摘要。'

{
  printf 'repository=%s\n' "$repository_slug"
  printf 'worktree=%s\n' "$repo_root"
  printf 'product_target_sha=%s\n' "$product_target_sha"
  printf 'test_commit_sha=%s\n' "$test_commit_sha"
  printf 'fixture_tree_sha=%s\n' "$fixture_tree_sha"
  printf 'adapter_pin=%s\n' "$adapter_pin"
  printf 'uv_cache_dir=%s\n' "$UV_CACHE_DIR"
  printf 'candidate_summary_sha256=%s\n' "$candidate_summary"
  printf 'gate2_status=NOT_APPROVED\n'
  printf 'formal_s3_rt_codex_1=NOT_RUN\n'
} > "$evidence_dir/metadata.txt"

printf '本地候选摘要：%s\n' "$candidate_summary"
printf '产品目标提交：%s\n测试提交：%s\n' "$product_target_sha" "$test_commit_sha"
printf '证据目录：%s\n' "$evidence_dir"

run_suite judge test_issue66_runtime_judge.py 63 PASS '' 0
run_suite credential test_issue66_invocation_credential.py 17 PASS '' 0
run_suite local_state test_issue66_stage3_local_state.py 12 PASS '' 0
run_suite validation_handoff test_issue66_validation_handoff.py 21 PRODUCT_FAIL \
  'test_new_invocation_can_prepare_round_one_after_prior_terminal_validation' 1
run_suite agent_contract test_stage3_idea_generator_agent_contract.py 9 PRODUCT_FAIL \
  'test_opencode_example_and_common_closeout_follow_skill_handoff_chain' 3

candidate_manifest_after="$evidence_dir/candidate-files.after.sha256"
write_candidate_manifest after "$candidate_manifest_after"
capture_required candidate-summary-after shasum -a 256 "$candidate_manifest_after"
candidate_summary_after=''
read -r candidate_summary_after _ < "$evidence_dir/commands/candidate-summary-after.stdout"
if [[ "$candidate_summary_after" != "$candidate_summary" ]]; then
  printf 'INVALID_TEST_EXECUTION\t候选文件在执行期间发生变化。\n' > "$evidence_dir/outcome.txt"
  printf '候选文件在执行期间发生变化；本次证据不能绑定到单一候选。\n' >&2
  exit 2
fi

suite_results="$(<"$suites_tsv")"
if [[ "$suite_results" == *'INVALID_TEST_EXECUTION'* ]]; then
  overall='INVALID_TEST_EXECUTION'
  exit_code=2
elif [[ "$suite_results" == *'PRODUCT_FAIL'* ]]; then
  overall='FAIL'
  exit_code=1
else
  overall='PASS'
  exit_code=0
fi
printf 'candidate_verdict=%s\nrunner_execution=COMPLETE\n' "$overall" > "$evidence_dir/outcome.txt"
printf 'candidate_verdict=%s\n' "$overall" >> "$evidence_dir/metadata.txt"
printf 'evidence_directory=%s\n' "$evidence_dir" >> "$evidence_dir/metadata.txt"
printf '运行完成：%s；退出码 %d；证据目录：%s\n' "$overall" "$exit_code" "$evidence_dir"
exit "$exit_code"
