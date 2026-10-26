# 轻量 handoff 正文 future-work — 测试计划与 recipe

- Revision CONTACT-SOURCE-TP1.1，配对 CONTACT-SOURCE-EP1.1（全局章节白名单修正仍由T5覆盖；T4空fixture改为非空旧候选）。
- Baseline contact `18fd48d1b6f2e26241c304d6acddb025297f08e4`；上游接口核对 `7b086ef361db54e2d3f6e333145a750ff56a48dc`。正式执行记录实际候选与使用的 helper SHA，不把这些 baseline 当已实现版本。
- Proposed review status: pending；测试设计与 Gate1 见 `review.md`；Gate2 的 helper 运行资源接线已补入 recipe 与准备记录、待确认；Gate3 未执行。本 PR 提交计划与测试准备资产，不修改产品代码。规则及授权见执行计划。

## 必测清单（验收上限）

| ID | 目标/输入 | 预期 | 足够的检查 |
|---|---|---|---|
| T1 | 有完整 prepare、候选外正文一句，另带一个旧合法候选，生成并导入 source-items-v1 | 返回项不需候选ID；正式 sidecar 含两条及正确页/源SHA，既有候选ID保留，facts正确join；ZIP/临时目录无 PDF，原 PDF 不变 | 现有 unittest 框架中的一个 focused build→import 用例；调用真实 paper-analysis helper，不 mock 原文校验结果 |
| T2 | 旧 prepare 无 source_pages；同源缓存为一个必要坏页提供正文 | 统一 helper 补齐，原 prepare/candidates 不变；transport 与新 prepare 使用同一页文字，缺该必要缓存时 upload_ready=false，无 PDF fallback | 同一个准备路径 focused unittest，实际 helper prepare/merge，临时合成 PDF 和既有 cache格式；不调OCR服务 |
| T3 | T1 结果分别改错物理页/改写原话；当前源PDF变化 | 原文或身份校验失败，相应 job 不安装 analysis/sidecar/index；不改输入或放宽匹配求成功 | 现有断言/文件观察，最小三个变体；不扩 hash/并发/路径组合 |
| T4 | 旧 exact-items 的一个合法非空候选与旧 hybrid OCR excerpt结果 | 原协议成功；不把旧包静默解释成新 contract；有效候选不要求新字段 | 原有legacy bundle fixture保留一个真实候选，复用T1同一helper直接导入；另复用一条既有OCR selector，不跑所有legacy回归 |
| T5 | 生成 instructions 与两 runtime 调用说明 | 新契约正文可选，旧协议边界清楚；实际入口传完整prepare；无额外全文pass或PDF上传 | 人工阅读相关生成说明、两runtime与SKILL |

不重测上游 SourceLocator 的完整断词/跨页矩阵，当前算法未改。T1 引用可直接来自已读正文；真实两论文材料只作缺口定位，不要求重跑658篇或上传私有PDF。没有安装矩阵、浏览器、完整套磁流程、通用来源认证或新判定框架。

## 可执行 recipe（实现后执行，现在不运行）

1. 在隔离 contact producer checkout 中工作，使用已有可用 Python/helper依赖，临时输入与输出用 `RUN=$(mktemp -d /tmp/contact-source-evidence.XXXXXX)`；用例的临时目录由 `CONTACT_SOURCE_TEST_RUN_ROOT="$RUN/tmp"` 指定，标准输出存 `$RUN`。记录实际 Python/contact/helper版本和 RUN。不得读取用户生产教授目录或 Zotero；缺依赖记无法判断，不自动安装。
2. 在 `.apm/skills/professor-contact/tests/test_stage2_chatgpt_handoff_source.py` 用当前 `unittest`、`tempfile`、已有 handoff support 组织 T1–T3 及T4旧exact非空输入；合成小 PDF 包含已知正文和候选外语句，复用上游既有 fixture构造方式。只需要正常输出与明确变体，不新增测试工具。测试可写 disposable PDF作为原始输入；产品不得复制它。
3. 使用同一已安装 paper-analysis 的 `future_work.py/facts.py/pdf_runtime.py` 运行实际 helper，不 mock helper 的语义输出。本次准备固定以下运行资源（Gate2 项的实际值）：
   - skill：`/nix/store/vvdass0s4x1b2h46sqk29dq7rdbjbmr8-paper-analysis-0.1.0/payload/skills/paper-analysis`；其中 `future_work.py` SHA256 为 `25bd7678f85dc1a8cb527449f65f12d0b4400da5ff8d8806b26a175490d571ea`，与 flake.lock 的 paper-analysis `c140658cc60f9d9c3d17008cbab0b599f40c8e46` 同一文件内容一致。
   - agent：`/nix/store/vvdass0s4x1b2h46sqk29dq7rdbjbmr8-paper-analysis-0.1.0/codex/agents/paper-analysis.toml`。
   - 解释器：`/nix/store/447smjkzgapdxqrcdg8r8kf8j1a1jrxc-python3-3.14.7-env/bin/python3`（Python 3.14.7；`scholar-workflow-pdfx 0.1.0`、`pymupdf 1.27.2.3`），即该 paper-analysis 包 `agent-env.json` 的 runtimePackages 解释器。测试进程和 helper 使用同一解释器，并用它在临时目录生成合成 PDF。
   - 接线变量：`CONTACT_PAPER_ANALYSIS_SKILL`、`CONTACT_PAPER_ANALYSIS_AGENT`、`CONTACT_PAPER_ANALYSIS_PYTHON`。测试模块把解析到的解释器同步到产品已有的 `CONTACT_PAPER_PYTHON`，供 `_run_future_work` 调用同目录 `facts.py`。三者任一缺失时模块以 SkipTest 记未执行，不记通过；已设置但路径无效时按准备失败报错。store 路径丢失时按同一 flake.lock revision 重新求值，不换用其它 helper 版本。此为运行资源接线，不增加另一次真实 E2E证明。
4. T1–T4 模块入口（T4 exact 在同一模块，见第 5 步）。先导出第 3 节三个变量：
   ```bash
   RUN=$(mktemp -d /tmp/contact-source-evidence.XXXXXX)
   export CONTACT_PAPER_ANALYSIS_SKILL="<第3节 skill 路径>"
   export CONTACT_PAPER_ANALYSIS_AGENT="<第3节 agent 路径>"
   export CONTACT_PAPER_ANALYSIS_PYTHON="<第3节解释器>"
   export CONTACT_SOURCE_TEST_RUN_ROOT="$RUN/tmp"
   "$CONTACT_PAPER_ANALYSIS_PYTHON" -B -m unittest discover \
     -s .apm/skills/professor-contact/tests \
     -p 'test_stage2_chatgpt_handoff_source.py' -v 2>&1 | tee "$RUN/source-items.out"
   ```
   断言直接读 zipfile/JSON 和目标文件：新 contract、预期原话/页/ID/hash/facts关系、无PDF、必要拒绝和输入不变。JSON正式摘要用jq；不写额外采集器。
5. T4 exact 在同一新模块：沿用旧 embedded bundle构造（`_stage2_handoff_test_support.legacy_embedded_bundle(..., selection_contract="exact-items-v1")`），用T1中合法旧候选和真实helper，断言正式sidecar保留引用/页/ID，且候选外引文仍被旧协议拒绝；不采用原 `test_legacy_bundle_without_context_still_imports` 的空items与永远成功helper作为非空兼容证据。旧 hybrid 只执行：
   ```bash
   PYTHONPATH=.apm/skills/professor-contact/tests "$CONTACT_PAPER_ANALYSIS_PYTHON" -B -m unittest -v \
     test_stage2_chatgpt_handoff_review3.Review3RegressionTests.test_ocr_required_selection_rebinds_after_merge_without_external_candidate_id
   ```
   测试专用旧 embedded fixture不改变新产品默认。旧hybrid行为未改且已有适用结果时引用原记录免重跑，说明适用性。
6. T5 人工比较以下材料，确认任意已读正文中的作者明示可以选择、局限性不得推断为承诺：
   - 生成说明：`.apm/skills/professor-contact/scripts/stage2_chatgpt_handoff.py` 的 `_instructions()`（新契约正文可选、旧协议只作旧包兼容说明）。
   - 两 runtime 调用说明与全局原则：`packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 的 Step 4.5 A/C、future work 与局限的原则段和禁止事项。
   - SKILL 的 handoff 简短说明：`.apm/skills/professor-contact/SKILL.md`。
   人工一致性阅读已足够，不额外运行旧 workflow assertion。本模块已登记 `plan/test-grouping/shards.json` 的 shard4（stage2）；用既有 `python3 scripts/check_test_shards.py` 检查索引，不跑全部 shards。
7. 保存首轮及修正尝试标准输出于 RUN（如 `$RUN/source-items.out`），提交必要脱敏结果到本目录；每项记录通过/业务失败/无法判断/未执行。文档SHA不触发重跑；修复仅重跑受影响项。

## 准备与预检记录（2026-10-27）

- 目标版本：contact `2866b1cdfa39f8a9ee19796cf063cfc4ef756c19`（PR #143 head）；paper-analysis helper 与解释器见第 3 节实际值。
- 已交付准备产物：
  - `.apm/skills/professor-contact/tests/test_stage2_chatgpt_handoff_source.py`：T1、T2（有/无必需页缓存两个准备路径）、T3（错页/改写原话/源 PDF 变化三个变体）、T4（旧 exact 非空候选与候选外拒绝）。
  - `.apm/skills/professor-contact/tests/_stage2_handoff_test_support.py`：`legacy_embedded_bundle` 新增可选 `selection_contract` 参数，并优先从 `bundle_dir` 读取 prepare/candidates 字节；默认参数与原调用行为不变。
  - `plan/test-grouping/shards.json`：新模块登记到 shard4（stage2）。
- 有限预检（临时目录 `/tmp/pr143-test-prep-20261027`，使用第 3 节解释器；未调用 contact build/import 正式入口，未执行必测用例）：
  - 三个 helper 脚本与解释器可用；helper `prepare` 在 5 页合成 PDF 上产出 `source_pages`/`page_quality`（5 页 trusted、`ocr_required_pages` 为空），候选外句不在 `candidates.json`。
  - 空白末页的合成 PDF 上 `prepare` 标 `ocr_required_pages=[5]`、第 5 页 tier=empty；按 `<pdf>.llm_ocr.pages.json` 既有格式写页缓存后，`pdf_runtime.py validate-ocr-cache` 与 `future_work.py merge-ocr` 成功，合并后 required 为空、第 5 页正文为缓存文字。
  - 计划中的 T1 两条 items（候选外 + 合法候选）经真实 helper `validate`/`finalize` 通过，sidecar 页码/ID/源SHA 与预期一致；改错物理页与改写原话均被拒绝；真实 `facts.py finalize` 产出 `future_work_ids` join。
  - 各测试类的 fixture setUp（合成 PDF、真实 prepare、旧 prepare 降级、页缓存写入、候选定位）逐类运行无错误。
  - `python3 scripts/check_test_shards.py` 返回 `OK: 83 test modules across 4 shards, each with a stage`。
- 未完成：Gate3 未执行；T5 待人工阅读；本轮没有正式通过结论。

环境不可用时停止受影响项；资源恢复或步骤实际修正后最多一次有理由重试，保留原结果。业务断言失败先诊断产品，不能换输入/放宽引用校验；需要改步骤时先修订受影响recipe。没有模型/provider外部重采样或安装授权。测试设计可独立审核，运行资源已按第 3 节与准备记录补齐，Gate2 仍待审核确认；作者不自授APPROVED/PASS。
