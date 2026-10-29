# 邮件 Markdown 支撑论文分析链接 — 测试计划

- Requirement R1 / execution EP1：[implementation-plan.md](implementation-plan.md)。
- Test plan revision TP1；目标基线 `ad096fe31a4b5694cbe47a40f37b621435e1eeec`。
- 独立审核：2026-10-29 主代理批准 TP1 G1 必测范围、G2 步骤；实际三项定向检查已执行；独立审核 TP1 G3 PASS，详见 [test-results.md](test-results.md)。用户已明确授权本次三个 contact PR 必要产品、测试及计划修改。

## 必测范围（上限）

|检查|业务目标与输入|预期/断言|
|---|---|---|
|T1 canonical 透传|直接调用真实 compile_email_entry，既有事实 pack 中两篇不同论文具有不同绝对 analysis_file；选择其中 paper 并引用另一篇 gap|输出按 item_key 精确保留各路径，不错配；无路径记录省略字段；不从 raw 产生路径；现有 source_hash 涵盖该新增事实|
|T2 内审渲染与旧包兼容|真实 render_source_table/render_fact_check_card，paper/later/gap 来源、有空格的中文日文真实路径；同例移除可选字段代表旧包|有路径输出相对教授目录的 `[分析](<...>)` 并保留对应 Zotero；无字段仍正常且仅 Zotero；支持无 gap 的 paper 来源，不将其它 paper 的路径串入|
|T3 实际输出边界|复用 TestStage5 的 CLI fixture，新增一个路径链接用例，经正常 plan/finalize 生成 md/txt|md 内审可见分析链接；md 邮件正文及 txt 与该 fixture 的 draft Subject+body 一致，不混入审阅链接|

T1/T2 使用一个轻量 unittest 文件 `test_email_analysis_links.py`，复用仓库 runner 导入/fixture 或标准库 unittest，不增加判定器/框架。T3 在既有 `test_contact_state.TestStage5` 增加 `test_stage5_email_analysis_links_are_md_only`，复用 prepare/raw_result/choices，不重放全仓测试。已有原始 full-flow 用例不是另增必测：新用例直接验证受影响输出，避免重复完整回归。若发现既有 fixture 有前置故障，记录该失败及阻塞，不为通过而扩大业务或伪造结果。

## G2 执行 recipe

审核通过并实现后，从仓库根目录运行（仅 Python 标准库和已有测试依赖；若缺依赖报告，不安装用户环境）：

```sh
RUN=$(mktemp -d /tmp/contact-email-analysis-links.XXXXXX)
git rev-parse HEAD > "$RUN/revision.txt"
git diff > "$RUN/candidate.diff"
cd .apm/skills/professor-contact/tests
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v \
  test_email_analysis_links \
  test_contact_state.TestStage5.test_stage5_email_analysis_links_are_md_only \
  > "$RUN/tests.log" 2>&1
rc=$?
cat "$RUN/tests.log"
printf 'exit_code=%s\n' "$rc"
```

成功标准：列出的检查全部正常结束并满足各用例业务断言；保留退出码和完整输出。临时业务输入输出由既有 TemporaryDirectory fixture 管理，仅在 `/tmp`，不触碰 Mac、真实教授数据、模型或外部服务。失败保留第一次记录，先归因；修复导致的新候选只重新运行直接受影响用例并记录新版本，不盲目重试、不追加测试矩阵。

## G3 结果记录

执行后在本目录追加独立结果记录，列出 candidate commit/diff、Python 版本、具体命令、每项结果、日志路径和未验证项。作者只陈述实际输出；独立 reviewer 评价 G3。Mac UI 点击表现及真实数据链接可达性未在云端实测，由用户后续验证；不将其扩大为本次额外模型/安装回归门槛。
