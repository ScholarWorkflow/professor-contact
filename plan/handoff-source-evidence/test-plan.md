# 轻量 handoff 正文 future-work — 测试计划与 recipe

- Revision CONTACT-SOURCE-TP1.1，配对 CONTACT-SOURCE-EP1.1（全局章节白名单修正仍由T5覆盖；T4空fixture改为非空旧候选）。
- Baseline contact `18fd48d1b6f2e26241c304d6acddb025297f08e4`；上游接口核对 `7b086ef361db54e2d3f6e333145a750ff56a48dc`。正式执行记录实际候选与使用的 helper SHA，不把这些 baseline 当已实现版本。
- Proposed review status: pending；Gate1/Gate2 待审；Gate3 未执行。本 PR 只计划。规则及授权见执行计划。

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

1. 在隔离 contact producer checkout 中工作，使用已有可用 Python/helper依赖，临时输入与输出用 `RUN=$(mktemp -d /tmp/contact-source-evidence.XXXXXX)`；记录实际 Python/contact/helper版本和 RUN。不得读取用户生产教授目录或 Zotero；缺依赖记无法判断，不自动安装。
2. 在 `.apm/skills/professor-contact/tests/test_stage2_chatgpt_handoff_source.py` 用当前 `unittest`、`tempfile`、已有 handoff support 组织 T1–T3 及T4旧exact非空输入；合成小 PDF 包含已知正文和候选外语句，复用上游既有 fixture构造方式。只需要正常输出与明确变体，不新增测试工具。测试可写 disposable PDF作为原始输入；产品不得复制它。
3. 使用同一已安装 paper-analysis `future_work.py/facts.py`（固定解释器或原 uv入口）运行实际 helper。明确在 fixture args 指定该脚本路径；不能 mock helper的语义输出。实现者在执行前将该实际路径/解释器补入本节并经 Gate2 确认；路径尚未确定不声称步骤可执行或结果通过。此为运行资源接线，不增加另一次真实 E2E证明。
4. T1–T3入口：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage2_chatgpt_handoff_source.py' -v`。断言直接读 zipfile/JSON和目标文件：新 contract、预期原话/页/ID/hash/facts关系、无PDF、必要拒绝和输入不变。JSON正式摘要用jq；不写额外采集器。
5. T4 exact检查放入上述同一个新模块：沿用旧 embedded bundle构造，用T1中合法旧候选和真实helper，断言正式sidecar保留引用/页/ID；不采用原 `test_legacy_bundle_without_context_still_imports` 的空items与永远成功helper作为非空兼容证据。旧 hybrid 只执行 `PYTHONPATH=.apm/skills/professor-contact/tests python -m unittest -v test_stage2_chatgpt_handoff_review3.Review3RegressionTests.test_ocr_required_selection_rebinds_after_merge_without_external_candidate_id`。测试专用旧 embedded fixture不改变新产品默认。旧hybrid行为未改且已有适用结果时引用原记录免重跑，说明适用性。
6. T5 人工比较实际 wrapper instructions、两 analyzer Step4.5、同文件全局原则/禁止事项的章节来源限制与 SKILL，确认任意已读正文中的作者明示可以选择、局限性不得推断为承诺；人工一致性阅读已足够，不额外运行旧workflow assertion。若新测试模块需要登记现有 shard inventory，仅登记本模块并用既有 `python scripts/check_test_shards.py` 检查索引，不跑全部shards。
7. 保存首轮及修正尝试标准输出于 RUN，提交必要脱敏结果到本目录；每项记录通过/业务失败/无法判断/未执行。文档SHA不触发重跑；修复仅重跑受影响项。

环境不可用时停止受影响项；资源恢复或步骤实际修正后最多一次有理由重试，保留原结果。业务断言失败先诊断产品，不能换输入/放宽引用校验；需要改步骤时先修订受影响recipe。没有模型/provider外部重采样或安装授权。测试设计可独立审核，运行资源路径补齐前 Gate2保持待完成；作者不自授APPROVED/PASS。
