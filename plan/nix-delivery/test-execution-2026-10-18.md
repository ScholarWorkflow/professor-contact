# professor-contact Nix 交付执行记录（N1–N4）

- 产品提交：`a9999284`（PR #93 head；`CONTACT_REF=github:ScholarWorkflow/professor-contact/<head SHA>`），内容 = 实现 `48172e4` + `origin/main`（PR #91）合并
- 早前被验提交：`af6bf55c4e3afd456832be0289338c454ec37cc2`（N1–N4 首轮全绿）与 `48172e4fee7b273febdda81c152b0a8ce2773932`（审核跟随修改后全绿）；见第 5、6 节
- 依据：[执行计划 R3](implementation-plan.md)、[测试计划 TP5.1](test-plan.md)、Test Engineer Rule、Project Consensus
- 运行目录（仓库外）：合并后 `/tmp/contact-nix.Zc1wnW`（consumer=`$RUN/consumer`，样本=`$RUN/data`，输出=`$RUN/output`，夹具=`$RUN/evidence`）；`48172e4` 用 `/tmp/contact-nix.1ilKkF`；首轮 `af6bf55` 用 `/tmp/contact-nix.27Uu6n`
- 本轮执行：N1、N2、N3、N4.2 在合并后提交重跑；N4.1 按未受影响复用 `af6bf55` 结果（依据见 4.1）；未执行项见第 4 节
- 证据位置：`$RUN/output/`（`n1-*`、`n2-*`、`n3-*`、`routes.json`、`abstract-export/`）、`$RUN/evidence/`（fixture、item key、endpoint）

## 1. 依赖与固定版本

| 依赖 | 固定提交 | 说明 |
| --- | --- | --- |
| agent-env-nix | `2158e933aab6c845ae1ceb1228458d624f8777d5` | 共享安装器（`mkAgentPackage`/`mkProject`） |
| paper-analysis | `eceade6b6d22a6114ecdd99b5a0c358869dfc798` | Stage 2 helper、`bin/future-work`/`bin/facts` |
| zotero-tools | `24eb6cf596c082ac005ccdd800b962fbb6a8e2c8` | 锁定 `bin/zotero-item-export`、`zotero-read` |
| base-skills | `3ab2ac188e625b8a8ae37b5fa318c579787c3d1e` | `humanizer-ja`、`vision-tools`（与 paper-analysis 同一次求值） |
| pdf-processing-core | `3444dca0e0b84f46d1839ab5c707afa78e23d3a7` | 固定 Python（pdfx）与 `pdfx-agent`（formula-repair / llm-ocr-refresh） |
| knowledge-tools | `bdb0db128b7cfccc6a3b20a8d0acee8695d0e211` | `lib.mkKnowledgePackages` → `extraction-to-knowledge` 递归闭包 |
| skills-test-fixtures | `8cecafc694e4591dee47372f38903e5ac2b689fe` | N4 夹具 pin（与 PR90 recipe 相同） |

`zotero-tools` 保留其自有 lock（nixpkgs `55bfb4d7…`、agent-env-nix `ba2d0fe4…`），与 professor-research 叶子包的做法一致，避免同名不同 payload。

## 2. 逐项结果（合并后提交 a9999284）

### N1 构建与元数据：PASS

```sh
nix build "$CONTACT_REF#professor-contact-runtime" --out-link "$RUN/runtime"
nix build "$CONTACT_REF#professor-contact" --out-link "$RUN/package"
nix build "$CONTACT_REF#professor-contact-environment" --out-link "$RUN/environment"
```

三个输出在 aarch64-darwin 实际构建成功（exit 0，2026-10-18 02:21，日志 `/tmp/pr93-run/merged-n1.log`）；合并进来的 PR #91 runner 内容（`results-dir`）确认进入安装树。

- `$RUN/package/agent-env.json`：`id=professor-contact`、`version=0.1.0`、1 个 skill、8 个角色（`professor-contact`、`-analyzer`、`-downloader`、`-idea-generator`、`-selection`、`-email-generator`、`-email-validator`、`-style-validator`）、6 个直接依赖、1 个 runtimePackage。
- 角色 TOML 全部按 `name`/`description`/`developer_instructions` 解析通过，8 个名字唯一；analyzer 来自 `packages/professor-contact-codex/.apm/agents/`（正文含 Codex 原生委派契约）。
- 包级 override 求值：`(professor-contact.override { enableHarnesses = []; }).passthru.agentEnv.enableHarnesses` = `[]`；默认 = `["codex"]`。
- environment manifest 的递归闭包：`professor-contact`、`paper-analysis`、`zotero-tools`、`humanizer-ja`、`vision-tools`、`scholar-workflow-pdfx-agent`、`extraction-to-knowledge`、`kb-importer`、`personal-knowledge-runtime`（9 个包、12 个 skill）；MCP 只有 `personal-knowledge`，owner 为 `personal-knowledge-runtime`。同名不同 payload 的冲突由 `mkProject` 拒绝，本次求值未出现。

### N2 实际安装与静态比对：PASS

```sh
mkdir -p "$RUN/consumer/.agents/skills/unrelated-sentinel"
printf 'keep\n' > "$RUN/consumer/.agents/skills/unrelated-sentinel/marker"
"$RUN/environment/bin/agent-env" apply --project "$RUN/consumer"
```

- `agent-env: apply completed.`；`$RUN/consumer/.agents/skills/` 得到 12 个受管 skill，无关 `unrelated-sentinel/marker` 仍为 `keep`。
- `$RUN/consumer/.codex/agents/` 得到 12 个角色 TOML（professor-contact 8 个 + paper-analysis 1 个 + pdfx 3 个）。
- 安装树与源目录 `diff -r`：差异仅为 R3 允许的三类——`SKILL.md`（追加 Stage 5 路由附录）、`docs/stage5-routing.instructions.md`（随资源复制的附录原文）、七个同目录薄入口（固定解释器与两处绑定）；其余正文逐字节相同（`$RUN/output/n2-static-diff.txt`，源侧 `__pycache__` 为本地未跟踪产物，不在安装树）。
- `scripts/_stage2_chatgpt_handoff_impl.py`、`scripts/stage5_immutable.py`、`scripts/stage5_immutable`、`docs/stage5-legacy-contract.md` 均存在；Stage 5 路由附录实际进入安装 `SKILL.md` 与 coordinator `developer_instructions`；email-generator 角色的 `stage5-finalize` 调用为 `<professor-contact-skill-dir>/scripts/stage5_immutable stage5-finalize`，不含 `skillrepo exec`。
- 固定运行环境记录：`$RUN/output/n2-handoff-binding.txt` 显示 `CONTACT_PAPER_PYTHON` 绑定到 `/nix/store/447smjkzgapdxqrcdg8r8kf8j1a1jrxc-python3-3.14.7-env/bin/python3`，与该入口第一行 shebang 及 `n3-fixed-python.txt` 为同一路径。

### N3 安装态本地入口：PASS

- `scripts/contact_targets preview`：`status=ok`、教授为「安装样本教授」、`dir_fixture` 的 `paper_count=1`（`$RUN/output/preview.json`）。
- `scripts/stage2_input_router`（无 locator，入口自带锁定 exporter）：合成 PDF 路径含空格，单条路由 `item_key=NIXTEST1`、`carrier=pdf`、`level=fulltext`、`paper` 等于规范化绝对路径、`gap_only_allowed=true`；`$RUN/output/router/NIXTEST1.json` 不存在，未触发摘要导出。
- handoff 固定解释器（安装树内、复用既有确定性用例）：

```sh
env -u CONTACT_PAPER_PYTHON "$FIXED_PYTHON" -B -m unittest -v \
  test_stage2_chatgpt_handoff.HandoffTests.test_future_work_selection_is_finalized_locally_via_uv_run
CONTACT_PAPER_PYTHON="$FIXED_PYTHON" "$FIXED_PYTHON" -B -m unittest -v \
  test_stage2_chatgpt_handoff.HandoffTests.test_future_work_selection_is_finalized_locally_via_configured_python_backend
```

两条都实际执行并 `ok`（第二条不是 `skipped`）：未绑定时仍走 `uv run`，绑定后 `_run_future_work` 用 `[固定解释器, script, …]` 启动 `future_work.py` 与相邻 `facts.py`，fake uv 日志中没有这两次调用（`$RUN/output/n3-handoff-unittest.log`）。该断言只证明「绑定后不再经过 uv」，实际绑定的解释器路径由 N2 的薄入口记录核对。

### N4.1 安装角色一次真实 Codex 调用：PASS（复用首轮，未受影响）

首轮在 `af6bf55` 上执行：夹具 `tests/runtime/prepare_issue53_stage4_fixture.py` 生成第 53 号 Stage-4 合成程序（pre 快照两个程序级文件均 absent）；`$RUN/consumer/.codex/config.toml` 合并 pin 的 `configs/codex-nested-delegation-consumer.toml`（`model=gpt-6-luna`、`model_reasoning_effort=low`、`sandbox_mode=workspace-write`、`features.multi_agent_v2.enabled=true`，保留安装写入的 MCP 表）；唯一 `/eval` 请求（既有服务 `127.0.0.1:17902`）HTTP 200；`selection-verdict.json` `status=pass`、`classification=PASS`；适配器确认正式委派关系 `formal_spawn_relation`（1 个 child thread，`expected_agent=professor-contact-selection`），child 返回 `needs_input`（`DIR00001`，候选 `idea-001`/`idea-002`），post 快照程序级文件仍 absent。

复用依据：最终提交与首轮之间，安装态 `professor-contact-selection.toml` 逐字节相同（两轮 SHA-256 均为 `f6519195780aaa0eaab7bbf1ffc17f2f414ebd9460e708ca36c2c1823c70a01d`，`$RUN/output/n4.1-selection-toml-sha256.txt`）；本项不经过 router、analyzer 或文档。首轮证据保留在 `/tmp/contact-nix.27Uu6n/output/selection-*`。

### N4.2 真实摘要导出（复用 PR90 recipe）：PASS

- 夹具：合并后运行目录内新 clone 的 `skills-test-fixtures@8cecafc…`（pin 与干净检查通过）；`prepare_shared_test_assets_macos.sh` 复用共享资产缓存（`fixture_repo_sha=8cecafc…`、`fixture_repo_dirty=no`）；`start_zotero_test_fixture_macos.sh` 启动隔离实例（`FIXTURE_KIND=zotero`、`FIXTURE_RUN_ID` 匹配、pin 匹配、checkout 干净），端点 `http://127.0.0.1:24120/mcp`。
- 合成条目：经 Zotero MCP `write_item` 写入一条有摘要无 PDF 的 `journalArticle`，`ITEM_KEY=IWBGDZU5`（`48172e4` 轮的 `CHZ62RYD` 记录保留在 `/tmp/contact-nix.1ilKkF`）。
- 导出：安装态 `scripts/stage2_input_router --papers … --output-dir …`（不传 `--zotero-read-skill-dir`，入口绑定锁定 `bin/zotero-item-export`），router exit 0、stderr 为空；路由 `carrier=abstract_json`、`level=abstract`、`status=ok`；导出文件 `.schema=1`、`.kind=paper-analysis-input`、`.source=zotero`、标题与摘要与预置值逐字节一致（`abstract_length=83`），摘要非空（`$RUN/output/abstract-export/export-summary.json`）。
- 结束后只用 starter 的 `stop` 收尾，并保留该 fixture 的 run 目录副本（`$RUN/evidence/fixture-logs/`）。

## 3. 附带的仓库回归

- 命令：`python3 -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py'`（与 CI 相同）：合并 `origin/main` 后 1022 条 `OK`、1 条 `skipped`（即未绑定 `CONTACT_PAPER_PYTHON` 时不适用的安装态用例）；`af6bf55`/`48172e4` 两轮各 1016 条 `OK`、1 条 `skipped`。
- 因 R3 改变源调用前缀，15 个既有源契约用例（18 个 case）的期望字符串由 `python3 …/scripts/<name>.py` 改为 `<…>/scripts/<name>`、`skillrepo exec …` 改为安装目录入口、`zotero-mcp-session` 改为 `bash "<zotero-read-skill-dir>/scripts/new-session.sh"`；断言强度不变，仅改绑到新入口形态。改动前这些用例在同一份代码上 18/18 失败，改绑后全绿。

## 4. 未执行与受限项

- **professor-collector 依赖边未交付**：professor-research 在 `24769bba…` 没有 `professor-collector` 的 Nix 包（该仓库 PR #35 仍是计划）。因此本环境不含 contact 的 Stage 1 缺 PDF 补齐边与 Stage 5 contact-evidence freshness 上游边，也不含 `professor-collector` skill。计划明确禁止填占位 SHA 或手拷上游，故按「实施顺序前置」记未执行，等该生产者发布实际包后按其提交补入；受影响的只有这两条业务路径，N1–N4 其余检查独立成立。
- 未验证：Zotero/浏览器/知识库服务自身的完整业务链、OCR 与真实论文分析、KB 写入、邮件生成与发送；这些不在 N1–N4 范围。
- 本记录不声明 Gate3 通过或可合并；第三关口由测试计划负责人按 TP5.1 审核。

## 5. 实现符合性审核与跟随修改

首轮审核（对象 `fb9a232`，含实现 `af6bf55`）结论「完整」，无阻断项、无需修项，3 条建议。最终提交 `48172e4` 做了三处跟随修改（都不改变业务语义）：

1. analyzer 源中补上直接调用 `pdfx`/`vision-glance` 时的安装形态选择说明（与既有 future-work/facts 说明同形），落实 R3「在唯一源中说明按已加载依赖的安装形态选择该 owner 的现有固定入口」。
2. 入口文档措辞限定为「按 `<skill-dir>/scripts/<name>` 直接执行时固定解释器」（README 与 `nix/contact.nix` 注释），对应审核建议 1。
3. router 入口在 `--zotero-read-skill-dir` 缺值时原样保留 argv，让 router 自己的 argparse 报告缺参（对应审核建议 3）。

未采纳的建议 2（SKILL.md 两处裸相对 `scripts/contact_state`）：该形态在基线 `d7d3024` 即为相对路径（原 `python3 scripts/contact_state.py`），属既有约定，本次不扩大改动范围。

## 6. 环境记录

- Nix 2.34.8（`aarch64-darwin`）、python3 3.14.7、jq 1.8.2、yq 4.54.1、uv 0.12.22；既有 eval 服务监听 `127.0.0.1:17902`（未启动/停止）；`/Applications/Zotero.app` 存在。
- N1–N4 命令按 TP5.1 原样执行；只在会话文件沙箱仍生效的早期本地迭代中使用过独立 `XDG_CACHE_HOME`，正式运行使用默认 Nix 缓存与默认 `HOME`，未改认证或全局安全设置。
- 未修改产品以迎合测试；未因提交编号变化重跑未受影响项（N4.1 复用并给出逐字节依据）。

## 6. main 同步（PR #91）与影响分析

`origin/main`（`07957d1`，PR #91 stage-2 runner fixes）与本分支只在两个 analyzer 的 Stage-2 `resolve-plan` 命令块冲突；解决方式为两侧都保留：main 新增的 `run_dir=$(mktemp -d …)` 与 `--results-dir "$run_dir"`，加上本分支的同目录入口前缀。合并后 `git diff` 无冲突标记，且未再出现 `python3 …/scripts/<name>.py`、`skillrepo exec …` 形式的可执行命令。

影响分析（按 R3「PR91/92 合并后只分析受影响文件并更新 pin」）：

- PR #91 只改了七个入口对应脚本中的 `contact_state.py`（内容变化，入口接口与 staging 替换点不变），另加 SKILL.md、两个 analyzer、style-validator 与测试；`flake.nix`/`flake.lock`/七个入口/`nix/contact.nix` 的依赖 pin 不需要更新。
- 因此重新执行 N1（构建与元数据）、N2（安装与静态比对）、N3（安装态入口）与 N4.2（真实导出）；N4.1 复用依据仍然成立（两轮安装态 `professor-contact-selection.toml` 逐字节相同，SHA-256 均为 `f6519195780aaa0eaab7bbf1ffc17f2f414ebd9460e708ca36c2c1823c70a01d`）。
- 合并后仓库回归 1022 OK / 1 skipped。

## 7. 实现符合性审核记录

- 首次审核（对象 `fb9a232`，含实现 `af6bf55`）：结论「完整」，无阻断项/无需修项，3 条建议；三处跟随修改与一条未采纳理由见第 5 节。
- 定向复核（对象 `fb9a232..3c02bf9`）：结论「完整」，逐行确认三处跟随修改只在 R3 允许范围、router 缺值分支仍 fail closed 且保留原 stdout/stderr/退出码、记录如实；3 条观察（记录措辞、既有 `--zotero-read-skill-dir` 后接 flag 的既有边界、夹具 starter 日志片段）均不阻断。
- 合并 `origin/main` 后由同一审核角色做最后一次极小复核（范围：两个冲突块的解决与记录更新）。
