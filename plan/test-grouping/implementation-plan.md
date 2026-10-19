# 测试分组与 CI 分片（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18“其余边界”原文中的“测试分组／CI：可以另评估快审，但不能只按 test_stageN 文件名筛选”。
- Requirement revision: 第 1 版。
- Canonical Plan revision: 第 3 版。
- Target repository revision: `6e624e0`（`origin/main`）。本批是独立工作，不改产品代码，也不依赖在途 PR 的合并顺序，因此从 `main` 另拉分支 `refactor-test-grouping`。
- Relevant upstream/runtime revision: CI 工作流 `.github/workflows/ci.yml`（当前单任务，Python 3.12）。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`，P1–P4 全 PASS；独立计划审核于 2026-10-18/19 给出）。
- 唯一规范来源：本文件。

## 正式需求与范围

- **R1 按实际行为分组**：分组依据必须是“测试实际驱动了哪个阶段的入口”（CLI 子命令、runner 入口点、基类继承），不得只按 `test_stageN` 文件名。**归类结果必须落到每个模块**（多数加权信号决定主导阶段，并列记 `mixed:*`，无信号记 `non-stage`），并**用于分片分配**，而不是只算一份统计。
- **R2 覆盖不丢**：任何分片方案都必须保证全部 `test_*.py` 模块被且仅被一个分片覆盖；新增测试模块若未归类，CI 必须失败而不是静默漏跑。
- **R3 CI 语义不变**：任一分片失败 → 聚合任务 `test` 失败；不跳过、不弱化任何断言；分支保护里的必需检查名仍是 `test`（`strategy.matrix` 会为每个组合生成独立检查，因此必须另加聚合任务，见方案第 3 条）。
- **R4 可读的分组证据**：映射表与分片清单进仓库——`shards.json` 的每个模块带 `stage` 与原始加权 `signals`，每个分片带阶段构成；README 给出逐模块的阶段与耗时，便于复核与后续调整。

**非目标**：不改任何测试代码或产品代码；不引入第三方测试框架；不做“按改动路径跳过测试”（runner 为共享核心，跳过风险高于收益）；不按阶段拆成多个 GitHub 检查项（保持单一 `test` 门禁，分片是它的内部并行）。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md`、`Plan Reviewer Rule.md`；测试设计按 `Test Engineer Rule.md`。

测量都在**目标修订**（worktree `refactor-test-grouping`，`git rev-parse --short HEAD` = `dcd3d0a`＝`6e624e0` + 本计划提交）上、用显式传入 worktree 路径重跑：

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 全套规模与耗时 | `Ran 1025 tests in 416.2s`，`OK (skipped=1)`（本地 macOS／Python 3.14.7） | `uv run --no-project <主检出>/.tmp_scripts/1020_time_tests.py <worktree>/.apm/skills/professor-contact/tests` |
| 收集口径 | `unittest.TestLoader().discover(..., 'test_*.py').countTestCases()` = **1025** | 同上 worktree |
| 耗时高度集中 | 前 5 个模块 215s（52%）：`test_contact_state` 82.8s／88 项、`test_contact_evidence_ladder` 45.2s／40 项、`test_stage3_validation_refine` 30.1s／18 项、`test_issue66_validation_handoff` 28.9s／12 项、`test_stage3_direction_groups` 28.4s／19 项；其余 73 个模块合计 201s | 同上 |
| 按行为分组的结果 | 156 个测试类 / 1033 个方法（**定义口径**）：stage3 347、无阶段信号 250、stage2 239、stage4 143、stage5 29、stage1 23、跨阶段混合 2 | `uv run --no-project <主检出>/.tmp_scripts/1020_test_stage_map2.py <worktree>/.../tests`（CLI 子命令权重 3 + runner 入口点权重 1，解析基类继承） |
| 两个计数口径不同 | 1033 是“类体内定义的 test 方法”，1025 是 unittest 收集到的用例数（mixin/继承与重名会拉开差距）；此外 map2 用**类名**做键，同模块重名类（`Sample`）与跨模块重名类（`FakeTransport`）会被合并，比严格 AST 计数少 2 类 2 方法 | 同上；本轮已核对 |
| 无阶段信号的模块 | 250 个方法属文档/工具类（eval request、安装器、委派校验、`test_contact_targets` 等），不驱动某个阶段的运行时 | 同上 |
| 现 CI 形态 | 单任务：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`，Python 3.12；近期运行 5m38s–8m3s | `.github/workflows/ci.yml` 与 PR 检查项 |
| 基类信号会跨文件 | 例：`test_stage2_preflight_malformed` 继承 `test_stage2_preflight.PreflightBase`，只扫单文件会漏判 | 源码 |
| 本机与 CI 环境不同 | 计时是 macOS／Python 3.14.7，CI 是 ubuntu-latest／Python 3.12；分片均衡依据在首次 CI 跑完后按实测更新 | 工作流与本次测量 |

## 方案

### 因果链

需求（按行为分组用于 CI，不能按文件名）→ 现行机制（单任务串行跑 1022 项、约 6.5 分钟，耗时集中在 5 个模块）→ 变更点（把模块按“行为信号 + 实测耗时”分到 4 个分片，用 GitHub Actions matrix 并行；加一个覆盖校验脚本保证并集完整）→ 行为变化（CI 仍跑全部测试、仍是单一 `test` 门禁，只是并行）→ 满足需求。

### 选定设计

1. **分片清单**：4 个分片。分配规则是**阶段分组驱动 + 耗时均衡**：先按阶段分组，整组能放进某片的余量（均分份额 ×1.15）就整组放进去（同阶段用例尽量同片），放不下的大组（`stage3` 21 个模块）再按实测耗时贪心拆到负载最小的片。清单**固定放在 `plan/test-grouping/shards.json`**（覆盖脚本与工作流都读它），每个模块带 `stage` 与 `signals`，每个分片带 `stages` 构成：

| 分片 | 规模 | 模块耗时合计 |
| --- | --- | --- |
| 分片 1 | 38 个模块 | 104.0s |
| | `test_contact_state` `test_resolved_direction_preflight_integration` `test_stage2_chatgpt_handoff` `test_issue81_verify_cache_contract` `test_stage2_resolve_fingerprint_scope_regression` `test_stage2_narrative_example_contract` `test_opencode_depth_install` `test_issue74_cli_compat` `test_issue32_eval_request` `test_issue40_r2_verifier` `test_apm_deployment_metadata` `test_codex_native_delegation_contract` `test_contact_targets_gate2_oracle` `test_fixture_support` `test_gate2_evidence` `test_issue39_eval_request` `test_issue51_delegation_verifier` `test_issue51_standalone_runtime_recipe` `test_issue53_stage4_runtime_assets` `test_issue65_gate2_r24_regressions` `test_issue66_validator_report_contract` `test_issue67_riso_case_prep` `test_issue67_runtime_config` `test_issue67_runtime_evidence` `test_issue68_eval_request` `test_issue74_static_acceptance` `test_p47_target_isolation` `test_seed_issue39_zotero` `test_stage01_caller_contract` `test_stage1_stage2_contract` `test_stage1_stage2_contract_gate2_oracle` `test_stage2_chatgpt_handoff_review` `test_stage2_reference_id_repair_contract` `test_stage2_zotero_endpoint_contract` `test_stage3_stage4_caller_contract` `test_stage4_selection_agent_contract` `test_stage5_template_body` `test_verify_issue39_endpoint_runtime` | |
| 分片 2 | 13 个模块 | 104.0s |
| | `test_contact_evidence_ladder` `test_stage2_style_validation_handoff` `test_stage3_direction_identity` `test_issue61_direction_credibility_warning` `test_stage2_zotero_rpc_transport` `test_issue32_e2e_verifier` `test_stage5_fixture_isolation` `test_stage2_resolved_direction_acceptance_boundary` `test_stage2_chatgpt_handoff_review3` `test_issue57_runtime_assets` `test_stage2_resolved_direction_merge_fulltext_regression` `test_stage1_candidates` `test_prepare_issue40_runtime_fixture` | |
| 分片 3 | 14 个模块 | 104.0s |
| | `test_stage3_validation_refine` `test_stage2_resolved_direction` `test_stage2_preflight` `test_stage5_immutable` `test_build_issue29_stage2_fixture` `test_issue67_gate2_r3` `test_stage2_resolved_direction_fresh_review_regressions` `test_stage2_resolved_direction_regressions` `test_stage3_direction_identity_contract` `test_issue55_stage3_runtime_assets` `test_stage2_chatgpt_handoff_review5` `test_contact_targets` `test_build_issue32_e2e_fixture` `test_issue57_routing_stability` | |
| 分片 4 | 13 个模块 | 104.0s |
| | `test_issue66_validation_handoff` `test_stage3_direction_groups` `test_stage2_resolved_direction_downstream_regressions` `test_issue66_stage3_local_state` `test_stage2_facts_sidecar` `test_stage2_preflight_malformed` `test_issue66_r12_validation_input_sha` `test_stage2_preflight_binding` `test_stage2_input_router` `test_stage2_chatgpt_handoff_review4` `test_stage5_dualtarget_contract` `test_prepare_issue39_stage2_fixture` `test_stage1_handoff_identity` | |

   均衡依据：按模块耗时降序做贪心装箱，四片各 104.0s（串行合计 416.2s）。首次 CI 跑完后按 ubuntu／3.12 的实测更新本表与 `shards.json`。
2. **覆盖校验**：CI 第一步跑一个仓库内小脚本（`scripts/check_test_shards.py`）：枚举 `tests/test_*.py`，断言与分片清单的并集完全一致、无重复、无遗漏，**并断言每个模块都带阶段、阶段值属于文档化集合**（`stage1`…`stage5`／`non-stage`／`mixed:*`）。这样新增测试模块若忘了归类或阶段写错，CI 会红，而不是静默漏跑或丢掉对应关系。
3. **CI 变更（保持单一 `test` 门禁）**：
   - 新增 `shards` 任务：`strategy: matrix: shard: [shard1, shard2, shard3, shard4]`，每片先跑覆盖校验再跑自己的模块列表；
   - 新增聚合任务 `test`：`needs: [shards]`、`if: always()`，读 `needs.shards.result`，任一分片失败即失败，全绿则成功。
   - 这样分支保护里名为 `test` 的必需检查依然存在；matrix 组合只叫 `shards (shard1)` 等，不参与门禁。
4. **文档**：`plan/test-grouping/README.md` 记录映射方法与分片依据（含上表的统计与耗时），供后续调整。

### 冻结的契约

- 分片并集 = 全部 `test_*.py`；无重复、无遗漏（由覆盖校验脚本强制）。
- 每个分片命令可独立在本地跑通，且不依赖其它分片产生的文件。
- 全部测试仍然执行；跳过项仍按测试自身的 skip 语义。
- `test` 检查项仍是合并门禁：由 `shards` 之后的聚合任务提供该名字，任一分片失败即失败。
- 不改测试代码、不改产品代码、不改 Python 版本与依赖安装方式。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 保持单任务 | 可行但每次 6–8 分钟；分片是低风险优化（并行、不改测试） |
| 按 `test_stageN` 文件名分组 | 明确被需求排除：`test_contact_state`（88 项）与 `test_contact_evidence_ladder` 等文件名不带阶段，混合文件也多 |
| 按改动路径跳过测试 | runner 是共享核心，跳过会漏掉跨阶段回归；风险高于收益 |
| 按阶段拆成多个独立检查项 | 会让合并门禁变复杂（需要每个检查都通过）；保持单一 `test` 门禁更稳 |
| 用第三方并行测试框架 | 引入依赖与不透明行为；`unittest` 原生足够 |

## 影响

- **intended_change**：CI 由单任务串行改为 4 分片并行；新增覆盖校验脚本与分组文档。
- **preserved_behavior**：全部测试仍执行；断言与跳过语义不变；`test` 仍是合并门禁；本地命令仍可用（单条 `unittest discover` 依旧可跑全套）。
- **approved_behavior_change**：无产品行为变化。
- **prohibited_side_effect**：漏跑或重复跑测试；改动测试/产品代码；引入新依赖；把分片做成“按阶段只跑相关测试”。
- **unresolved impact**：GitHub Actions 计费按作业分钟数——4 个并行分片的总作业分钟略高于单任务（约 8 分钟 vs 约 7 分钟），换来的是墙钟时间下降（约 2–3 分钟）；若仓库对分钟数敏感，可退回 2 分片。

## 关键安全条件与反例

1. 覆盖校验脚本必须能对“漏归类”“重复归类”“清单里有不存在的模块”三种情况失败。
2. 分片并集必须等于发现到的全部 `test_*.py`（在 CI 的 Python 3.12 下同样成立）。
3. 任一分片失败，名为 `test` 的聚合任务必须失败（`needs` + `if: always()` + 读取 `needs.shards.result`）。
4. 分片列表里的模块名必须与文件名完全一致（含下划线），避免 `unittest` 静默不匹配。

反例：

- 只写 4 个模块列表而不加校验：将来新增 `test_stage6_*.py` 不会进任何分片 → 静默漏跑。
- 用 `unittest discover -k` 或路径前缀过滤代替模块列表：`-k` 匹配的是测试名而不是模块，容易多跑或漏跑。
- 分片里写 `test_contact_state`（无 `.py`）：`unittest` 会报模块不存在或静默跳过，必须显式校验存在性。
- 把 `test_contact_state` 与 `test_contact_evidence_ladder` 放进同一分片：该片约 128s，明显长于其它片，均衡失效（实测依据见事实表）。
- 只把任务名留作 `test` 而不加聚合任务：分支保护里名为 `test` 的必需检查永远不会出现（matrix 只生成 `test (1)`…），门禁静默失效。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**：
   - 新增 `plan/test-grouping/shards.json`（4 个分片与各自的模块列表）。
   - 新增 `scripts/check_test_shards.py`（**仓库根**的新目录；枚举 `tests/test_*.py` 并与 `shards.json` 比并集/重复/存在性，非零退出）。**不得放进 `.apm/skills/professor-contact/scripts/`**——那是随技能打包的产品目录，放进去会污染安装包。
   - 新增 `plan/test-grouping/README.md`（映射方法、测量命令与修订、两个计数口径、分片清单与依据、CI 环境差异）。
   - 修改 `.github/workflows/ci.yml`：新增 `shards` matrix 任务（先校验、再跑本片模块）与名为 `test` 的聚合任务。
   - 分片命令从 tests 目录执行（或设置 `PYTHONPATH`），否则 `python -m unittest <模块名>` 会导入失败；工作流里写明 `cd .apm/skills/professor-contact/tests`。
   - 不改测试与产品代码。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备（见同目录 `test-plan.md`）。
4. **正式执行**：本地跑覆盖校验与 4 个分片命令，核对并集等于全套；推 PR 后核对 CI 的 4 个分片结果。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 3 版：按审核的唯一阻塞项修正——把行为分组的**归类结果真正落实**：`shards.json` 的每个模块带 `stage` 与原始加权 `signals`、每个分片带阶段构成；分片分配改为阶段分组驱动（整组能放下就整组放，大组按耗时拆）；覆盖校验增加“每个模块都带阶段、阶段值属于文档化集合”两条断言；README 的逐模块阶段列改用真实归类结果（此前因键名带 `.py` 与不带 `.py` 不匹配而全为空）。
- 第 2 版：按第 1 轮审核的两条 blocker 修正——B1 全部测量改在目标修订（worktree）上重跑并写清命令、修订号、Python 版本与两个计数口径（收集 1025／定义 1033、类名做键会合并重名类）；B2 CI 改为 `shards` matrix + 名为 `test` 的聚合任务，保住单一门禁检查；另按 P4 精度项写明分片命令的工作目录、覆盖脚本放仓库根、分片清单固定在 `plan/test-grouping/shards.json`、CI 与本地环境差异的更新约定。

## 审核状态

计划第 3 版为当前唯一计划。第 1 版结论 `NEEDS_MODIFICATION`（B1、B2）已修正并取得 `Plan conclusion: APPROVED`；第 3 版按测试计划审核的唯一阻塞项（行为分组未落实）修正归类与分配，方案目标与范围未变。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
