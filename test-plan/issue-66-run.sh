#!/usr/bin/env bash
set -euo pipefail

readonly expected_worktree='/Users/rekidunois/.codex/worktrees/issue-66-test-engineer/professor-contact'
readonly expected_pr_head='dfe430560b6e4d9d85c30b71b8c84bc621da7549'
readonly expected_plan_sha256='e042ca1b07ff8e8196d477eb79d9552cf103172da8db0eb0108c4df218e1bb61'
readonly approval_marker='ISSUE66_GATE2_APPROVAL_R4: APPROVED'
readonly repo='ScholarWorkflow/professor-contact'

stop() {
  printf '拒绝继续：%s\n' "$1" >&2
  exit 64
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/.." && pwd -P)"
[[ "$repo_root" == "$expected_worktree" ]] || stop '工作树路径与本地候选不一致。'

approval_id="${ISSUE66_GATE2_APPROVAL_COMMENT_ID:-}"
[[ "$approval_id" =~ ^[0-9]+$ ]] || stop '未提供有效的 ISSUE66_GATE2_APPROVAL_COMMENT_ID；Gate2 尚未批准。'
command -v gh >/dev/null 2>&1 || stop '找不到 gh，无法核实远端批准。'
command -v jq >/dev/null 2>&1 || stop '找不到 jq，无法解析批准记录。'
command -v shasum >/dev/null 2>&1 || stop '找不到 shasum，无法固定候选摘要。'

actual_plan_sha256="$(shasum -a 256 "${script_dir}/issue-66.md" | cut -d ' ' -f 1)"
[[ "$actual_plan_sha256" == "$expected_plan_sha256" ]] || stop '本地权威记录摘要已变化；须重新审核候选并更新门禁。'

pr_head="$(GH_HOST=github.com GH_PROMPT_DISABLED=1 gh api "repos/${repo}/pulls/73" --jq '.head.sha')" || stop '无法读取 PR 当前 head。'
[[ "$pr_head" == "$expected_pr_head" ]] || stop 'PR head 与本地候选固定版本不符。'

approval_json="$(GH_HOST=github.com GH_PROMPT_DISABLED=1 gh api "repos/${repo}/issues/comments/${approval_id}")" || stop '无法读取指定的 Gate2 批准评论。'
jq -e \
  --arg issue_url 'https://api.github.com/repos/ScholarWorkflow/professor-contact/issues/73' \
  --arg marker "$approval_marker" \
  --arg plan_sha "$expected_plan_sha256" \
  --arg head "$expected_pr_head" \
  '(.issue_url == $issue_url)
   and (.body | contains($marker))
   and (.body | contains("candidate_sha256: " + $plan_sha))
   and (.body | contains("target_pr_head: " + $head))' \
  <<<"$approval_json" >/dev/null || stop '评论不属于 PR #73，或未逐字批准本候选摘要及目标提交。'

cat <<'RUNBOOK'
Gate2 批准评论已核实。此脚本只显示固定顺序，不执行安装、测试、服务操作或正式请求。

1. 固定 `uv --version` 与 `uv run --python 3.14 python --version` 的输出，确认工作树和批准评论指向同一候选。
2. 只读核对指定提交的锁文件、源文件与安装投影；确认完整目标提交、无手工补丁、初始输入摘要正确、禁止产物缺席。
3. 通过 `direnv exec .` 解析 `EVAL_PORT`，只读核对现存评估服务的进程环境和配置覆盖。不得启动、停止或重启服务。
4. 只读核对服务实际使用的数据库和运行记录路径；若未设置数据库目录，检查进程是否继承 `CODEX_SQLITE_HOME`。确认服务、数据库、日志均为测试专用，不读取顶层旧数据库作归属推断。
5. 固定共享环境提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`、适配器 `skills-test-fixtures/codex-eval-adapter@16` 和共识指定请求配置。建立本次独占证据目录并保存请求前的存在性、类型、完整字节快照。
6. 确认两项本地产品 FAIL 已按获批处置完成，且无未解决的 Gate2 阻断；否则停止，不发正式请求。
7. 按冻结的 `S3-RT-CODEX-1` 路径仅向现存 `/eval` 发出一次请求，保存完整原始响应、`app_server_events`、标准输出和错误输出。不得用新服务、`curl`、替代会话或命令摘要代替正式委派及真实入口证据。
8. 按 r4 运行判定程序，关联正式发送方、真实调用编号、子线程、轮次、工具调用及结构化返回；比较原文 UTF-8 字节、保存与记录摘要、写权限和完成顺序，输出唯一结论及逐项证据来源。
9. 对同一受保护文件集合保存请求后的存在性、类型和完整字节快照；保留所有尝试。遇到外部失败立即停止，不自动重试；复验前记录恢复事实和批准的复验决定。
RUNBOOK
