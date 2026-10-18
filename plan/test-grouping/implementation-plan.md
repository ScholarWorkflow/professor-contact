# 测试分组与 CI 分片（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18“其余边界”原文中的“测试分组／CI：可以另评估快审，但不能只按 test_stageN 文件名筛选”。
- Requirement revision: 第 1 版。
- Canonical Plan revision: 第 1 版。
- Target repository revision: `6e624e0`（`origin/main`）。本批是独立工作，不改产品代码，也不依赖在途 PR 的合并顺序，因此从 `main` 另拉分支 `refactor-test-grouping`。
- Relevant upstream/runtime revision: CI 工作流 `.github/workflows/ci.yml`（当前单任务，Python 3.12）。
- Proposed review status: pending。
- 唯一规范来源：本文件。

## 正式需求与范围

- **R1 按实际行为分组**：分组依据必须是“测试实际驱动了哪个阶段的入口”（CLI 子命令、runner 入口点、基类继承），不得只按 `test_stageN` 文件名。
- **R2 覆盖不丢**：任何分片方案都必须保证全部 `test_*.py` 模块被且仅被一个分片覆盖；新增测试模块若未归类，CI 必须失败而不是静默漏跑。
- **R3 CI 语义不变**：任一分片失败 → 检查失败；不跳过、不弱化任何断言；`test` 检查项仍作为合并门禁。
- **R4 可读的分组证据**：映射表与分片清单进仓库，附测量依据（模块耗时），便于复核与后续调整。

**非目标**：不改任何测试代码或产品代码；不引入第三方测试框架；不做“按改动路径跳过测试”（runner 为共享核心，跳过风险高于收益）；不按阶段拆成多个 GitHub 检查项（保持单一 `test` 门禁，分片是它的内部并行）。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md`、`Plan Reviewer Rule.md`；测试设计按 `Test Engineer Rule.md`。

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 全套规模与耗时 | `Ran 1022 tests in 386.509s`，`OK (skipped=1)`（本地 Python 3.14.7，逐模块计时脚本） | `.tmp_scripts/1020_time_tests.py` 运行结果 |
| 耗时高度集中 | 前 5 个模块 208s（54%）：`test_contact_state` 79.6s／88 项、`test_contact_evidence_ladder` 46.9s／40 项、`test_stage3_validation_refine` 30.0s／18 项、`test_stage3_direction_groups` 26.2s／19 项、`test_issue66_validation_handoff` 25.7s／12 项；其余 73 个模块合计 178s | 同上 |
| 按行为分组的结果 | 155 个测试类 / 1030 个测试方法：stage3 347、无阶段信号 250、stage2 239、stage4 143、stage5 26、stage1 23、跨阶段混合 2 | `.tmp_scripts/1020_test_stage_map2.py`（CLI 子命令权重 3 + runner 入口点权重 1，解析基类继承） |
| 无阶段信号的模块 | 250 个方法属文档/工具类（eval request、安装器、委派校验、`test_contact_targets` 等），不驱动某个阶段的运行时 | 同上 |
| 现 CI 形态 | 单任务：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`，Python 3.12；近期运行 5m38s–8m3s | `.github/workflows/ci.yml` 与 PR 检查项 |
| 基类信号会跨文件 | 例：`test_stage2_preflight_malformed` 继承 `test_stage2_preflight.PreflightBase`，只扫单文件会漏判 | 源码 |

## 方案

### 因果链

需求（按行为分组用于 CI，不能按文件名）→ 现行机制（单任务串行跑 1022 项、约 6.5 分钟，耗时集中在 5 个模块）→ 变更点（把模块按“行为信号 + 实测耗时”分到 4 个分片，用 GitHub Actions matrix 并行；加一个覆盖校验脚本保证并集完整）→ 行为变化（CI 仍跑全部测试、仍是单一 `test` 门禁，只是并行）→ 满足需求。

### 选定设计

1. **分片清单**：4 个分片，按“行为信号为主、实测耗时为辅”均衡（每片约 90–100s）。清单进仓库（工作流内联或 `plan/test-grouping/shards.json`），每片一个模块列表。
2. **覆盖校验**：CI 第一步跑一个仓库内小脚本（`scripts/check_test_shards.py`）：枚举 `tests/test_*.py`，断言与分片清单的并集完全一致、无重复、无遗漏；不一致直接失败。这样新增测试模块若忘了归类，CI 会红，而不是静默漏跑。
3. **CI 变更**：`test` 任务改为 `strategy: matrix: shard: [1,2,3,4]`，每片跑自己的模块列表；工作流名与检查项名保持 `test`（matrix 下显示为 `test (1)`…`test (4)`，仍属同一检查）。
4. **文档**：`plan/test-grouping/README.md` 记录映射方法与分片依据（含上表的统计与耗时），供后续调整。

### 冻结的契约

- 分片并集 = 全部 `test_*.py`；无重复、无遗漏（由覆盖校验脚本强制）。
- 每个分片命令可独立在本地跑通，且不依赖其它分片产生的文件。
- 全部测试仍然执行；跳过项仍按测试自身的 skip 语义。
- `test` 检查项仍是合并门禁；分片失败 = 检查失败。
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
3. 任一分片失败，`test` 检查必须失败（matrix 的默认 `fail-fast` 与最终状态语义）。
4. 分片列表里的模块名必须与文件名完全一致（含下划线），避免 `unittest` 静默不匹配。

反例：

- 只写 4 个模块列表而不加校验：将来新增 `test_stage6_*.py` 不会进任何分片 → 静默漏跑。
- 用 `unittest discover -k` 或路径前缀过滤代替模块列表：`-k` 匹配的是测试名而不是模块，容易多跑或漏跑。
- 分片里写 `test_contact_state`（无 `.py`）：`unittest` 会报模块不存在或静默跳过，必须显式校验存在性。
- 把 `test_contact_state` 与 `test_contact_evidence_ladder` 放进同一分片：该片约 127s，明显长于其它片，均衡失效（实测依据见事实表）。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**：
   - 新增 `scripts/check_test_shards.py`（枚举 + 并集/重复/存在性校验，非零退出）。
   - 新增 `plan/test-grouping/README.md`（映射方法、统计、分片清单与依据）。
   - 修改 `.github/workflows/ci.yml`：`test` 任务加 matrix，4 个分片各跑自己的模块列表；先跑覆盖校验。
   - 不改测试与产品代码。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备（见同目录 `test-plan.md`）。
4. **正式执行**：本地跑覆盖校验与 4 个分片命令，核对并集等于全套；推 PR 后核对 CI 的 4 个分片结果。

## 修订记录

- 第 1 版：首次提交计划审核。

## 审核状态

计划第 1 版为当前唯一计划，状态为待审核。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
