# U5 r6/t6 实现与执行记录

- 日期：2026-10-22；角色：本地执行工程师；对象：PR #106。
- 有效范围：[执行计划 r6](implementation-plan.md)全部实现及[测试计划 t6](test-plan.md) §4.3.1、§4.3.3。r6 的批准见 [P1–P4 审核](https://github.com/ScholarWorkflow/professor-contact/pull/106#issuecomment-6317865160)。不重跑历史 Recipe 或四分片。
- 实现基线：`c900fd61776916358baf0f3e5da059e57b651a7b`；本轮产品提交：`a374049`、`9ce93ca`、`5393e54`、`78a617a`。原 main 为 `1d8f138`。
- 工作树按用户要求创建于项目父目录的 `worktree/pr106-execution-20261022`，未使用 Codex 托管。环境为 macOS、uv 0.12.22、Python 3.14.6、标准库 unittest；未使用共享 fixtures、外部模型或生产数据。
- 原始输出：`/tmp/u5-t6-vb94FC`；缓存、每例独占临时目录及人工检查输出均在该目录，原始日志不提交。

## 1. 完成的产物与实际接线

| 要求 | 实际产物与调用 |
|---|---|
| A：坏登记不能折叠为 unknown | facts owner 严格解析 index 及候选 entry；prepare 与普通上下文拒绝坏 JSON、坏容器、非法级别。空 `papers={}` 保持合法 unknown。 |
| B：首次真实读取与冻结值接受 | `freeze_stage2_sources` 对同次稳定 bytes 解析和计算摘要，保存完整正文/边车、声明、缺失状态和业务视图；`Stage2Context` 消费该材料。接受元数据从 F 纯构造，写后不重新取样。PDF 只保留原验证需要。 |
| C：输入、结果与一次修复 | prepare→facts→resolve→普通计划→结果绑定同一 companion/run；计划保存完整 `model_input`。结果按文件/任务/方向聚合封存，错轮、缺失、字节或输入变化拒绝；只有首次实际 `unknown_reference_id` 授权对应非法引用位置的一次机械修复，原失败集合保留。 |
| D–F：完整共同观察 | `stage2_complete_observation` / `stage2_compare_observation` 覆盖 selected 候选全集、消费源、存在状态、来源投影、级别、业务参数、resolved 与 freshness。普通 plan/resolve/finalize 首次检查和普通写前检查比较 F→O；preflight、锁后刷新及刷新写前比较 B→O。 |
| G–H：旧态分类在写入前 | 原 pack、正文及相关文件先保存原始快照；header/body/cache/validator 的 schema、轮次、phase、pending、results 和 pack 绑定在候选接受前检查。合法中间轮次保留；旧坏绑定不能由新候选反向认证。渲染后再检查完整来源及 A 快照，之后按原有限顺序写入。 |
| I：刷新字段 | 沿用已实现的同次正文与 ownership 输出，保留旧 `u1`、正文归属及非本次负责缓存；新增检查不重新定义成员、引用或两轮校验政策。I 的专门结果复用测试计划 §4.7。 |
| 正式入口 | runner 显式注入上述 owner；Codex、OpenCode analyzer 及主 SKILL 同步来源准备→冻结材料形成事实→完整读取本轮计划→同一分析代理判断→完整聚合→封存→接受。 |

## 2. 自动执行、修复与定向复验

两条正式命令均使用 t6 §4.3.1 的选择器及 `uv run --no-project python -m unittest … -v`，分别保存退出码，不因第一条失败跳过生命周期。日志中的失败都保留。

| 版本 | 命令/日志 | 实际结果 |
|---|---|---|
| `a374049` | 完整 33 项，`t6-direct.log`、`t6-direct.exit` | 12.311 秒，退出 1；24 通过、7 失败、2 错误。 |
| `a374049` | 生命周期，`lifecycle.log`、`lifecycle.exit` | 1.491 秒，退出 1；前置接受被旧输出目录的过严检查阻止，后续未到达。 |
| `9ce93ca` | 原九个未通过项，加入口检查位置变化直接影响的 resolved 方法；`t6-direct-recheck.log` | 10 项、3.866 秒，退出 1；9 通过，候选全集漂移后下一次 preflight 的方向原因仍缺 `artifact_changed`。 |
| `9ce93ca` | 原生命周期选择器，`lifecycle-recheck.log` | 5.632 秒，退出 1；已推进到原第 1381 行的人工正文/旧校验绑定分类，返回 `needs_decision`，应为 `error/validation_render_stale`。此前生命周期分支已执行，失败后的分支未到达。 |
| `5393e54` | 剩余候选漂移方法，加直接受旧态分类影响的 `test_new_business_needs_explicit_overwrite_and_loses_old_validation`；`t6-direct-recheck2.log` | 2 项、1.109 秒，退出 0，全部通过。 |
| `5393e54` | 原生命周期选择器，`lifecycle-recheck2.log` | 1 项、5.465 秒，退出 0，完整通过。 |

首次发现的问题与实际修复：

1. 产品未要求顶层来源投影完整；现与源段投影精确核对。只读冻结上下文的完整当前观察移至各正式命令入口，保留坏登记、身份及来源段即时拒绝，刷新后的只读夹具检查不再被旧消费观察抢先终止。
2. 产品把结果目录内所有旧 JSON 都算成本轮输入；现严格校验计划指定的封存文件及其 bytes/任务/方向，忽略本轮不消费的旧输出，空 jobs 仍须封存空集合。
3. 两个 guard 预期与读取包装器用 `/tmp` 字面路径，而产品沿既有规范路径使用 `/private/tmp`；测试只改真实文件路径比较。两处直接 prepare 补完整 papers 来源声明。全部业务断言和原因码预期不变；人工 B Recipe 同步规范路径。
4. 候选全集中、方向实际消费集外的材料变化已使教授级 process，但方向理由漏报；现共同观察的材料变化同时写出 `artifact_changed`/`artifact_missing`。
5. 无新业务且旧 validator 不能绑定人工正文时，普通接受现返回 `validation_render_stale`；真实新业务的显式覆盖、清除旧认证及刷新人工保护仍保留。

另在执行前修正三处坏容器夹具：原 `papers={}` 是合法无登记，改为实际非法的 `papers=[]`；两个选择器相应改名。原“坏结构不能绕过拒绝”的预期保留，历史错误判断见测试计划修正说明。

**当前有效结果**：33 个定向方法均有适用通过结果（未影响的首次 24 项复用；首轮九个未通过项经上述定向修复与复验通过），生命周期完整通过。不是把失败首个断言之后的未执行分支计为通过。未影响的旧统计、兼容、字节、lease 等结果按 t6 复用；未新增必测项。

## 3. t6 §4.3.3 人工执行

### B：完整供给与成功接受

在 `9ce93ca` 上按 Recipe 打开持久 Python 会话，使用既有 `AnalysisLevelBase`；先保存 A/B 分析、future-work 和 index 的原始 bytes、标准 SHA 与 stat，再真实 prepare。临时分支为 `tmpmzg3kq6z`，事务为 `consumption-xba6msvl`。接受时工作树已含随后提交为 `5393e54` 的两处产品修正，源材料及普通首次成功路径未改。

- 实际材料位置为 companion 的 `sources.materials[规范源路径]`，内容内嵌；用 `jq .` 展开 facts 与来源段，并用 `getpath` 展开 A 全文。完整 A/B 文本、两份 future-work 的全部 items/ID/quote 和完整 index 与 F0 文件逐项相等。标准 SHA、size、mtime_ns、ctime_ns 与预先保存值逐项一致。
- facts 文件声明、fulltext/abstract/null、引用及候选/相关身份与材料一致；target、Stage1 snapshot、catalog、ledger、年份及范围参数均为本轮视图。facts 未声明/不存在状态、C 无登记/无来源和空 freshness 视图均明确。材料没有借原可变文件替代正文；未新增 PDF 全文读取或摘要。
- 原 facts 保留这些已核对输入，真实 plan 生成 narrative/freshness jobs，写完整两方向结果并 seal；finalize `ok`。接受 guard 等于 F0，原源 bytes 不变。canonical A=fulltext、B=abstract、C=null，正文为“全文级 1 篇 · 摘要级 2 篇 · 未确认 1 篇（共 4 篇）”。
- 长期包的 `observation.materials` 只有 state/sha256/stat 有限投影，未保存完整 text/data 或 model_input。初次按字段名 `materials` 搜索返回 false 后，沿实际对象展开确认这是有限投影，未以名字判断产品失败。
- 早期真实读取注入已由修正路径后的原自动方法实际命中并通过，不需要额外读取 API 包装。

输出：`manual-b-session.log`、`manual-b-companion.json`、`manual-b-facts.json`、`manual-b-a-material.json`、`manual-b-full-materials-equal.log`、`manual-b-f0-digests.log`、`manual-b-pack-projection.json`、`manual-b-statistics.log`、`manual-b-finite-projection.log`、`manual-b-accepted-guards.json`。已执行清理。后续 `5393e54` 只改漂移分流和失效旧校验分类，不影响本次首次成功路径，结果复用。

### C：修改实际保存输入，保留原摘要与结果

独立分支 `tmpb58pr9n7/consumption-4k7g7lpx` 在 `a374049` 真实完成 prepare→plan→结果→seal。实际 `plan_file` 为 companion，`plan_path=["stage2_plan"]`；展开完整保存的四个 jobs，与本次返回输入核对一致。按 Recipe 只给第一个 narrative 的既有 `model_input.user_note` 追加 ` saved-input-drift`，不修改摘要或重新 plan/seal。

先保存业务/facts/结果/companion bytes；shell 的 `jq` 确认恢复唯一输入字段后整个 JSON 与原件相等。finalize 返回精确 `error/invalid_result_json`，消息为 `sealed stage2 plan or actual saved input changed`。原业务文件、facts、结果均不变，companion 保持注入后 bytes。执行时产品为 `9ce93ca` 的入口修正内容，未改保存输入校验；本例通过。输出为 `manual-c-session.log`、`manual-c-saved-inputs.json`、`saved-plan-before.json`、`saved-plan-mutated.json`、`manual-c-input-path.json`、`manual-c-only-one-change.log`；已清理。

### 两个 analyzer 与主入口

分别读取两个入口完整相关段落，按顺序和路径传递核对，未执行分析代理或以关键词断言代替：

| 入口 | 实际段落位置与结果 |
|---|---|
| Codex analyzer | Step 6.1（414）来源准备后 prepare、完整消费冻结材料并形成事实；6.1.5（465，完整读取在 481）同 run 的 resolve 输入由同一代理判断；普通 plan（545，完整读取在 554）传相同 run_dir；6.3（579）全部方向聚合后 seal、接受同集合；一次修复（605）保留原失败并限制到引用。全部步骤齐备。 |
| OpenCode analyzer | Step 6.1（422）；6.1.5（473，完整读取在 489）；普通 plan（548，完整读取在 557）；6.3（582）；一次修复（608）。逐条核对相同消费顺序、同 run/目录、截断继续读原保存文件、同一代理判断和聚合封存责任，全部齐备。 |
| 主 SKILL | early preflight 路由（238）与 U5 材料/接受顺序（240）明确慢路径来源准备、完整读材料/计划、完整聚合、封存、写前校验和一次受限修复；指向上述两个正式流程。 |

## 4. 实现审核与交接

专用 `implementation_reviewer` 首次审核产品 `cebcef3`，覆盖 r6 全部应交付产物和必要连接，包含此前未修改的 canonical/统计、lease、refine、runner、两个 analyzer、主 SKILL 和已有执行结果。认可 33 个方法、完整生命周期、人工 B/C 及 I 的适用结果，结论为“部分完成”，指出以下四项：

| 编号 | 实际修正（产品和测试同为 `78a617a`） |
|---|---|
| IR1 | `managed_snapshot` 原来只识别 LF 机器头，普通接受会误拒合法 CRLF。现复用已有字节分隔器，保留原始头、正文和严格 UTF-8 错误分类。既有合法 CRLF 方法补接普通 prepare→plan→seal→finalize，原期待不变。 |
| IR2 | 已封存 resolve 原来阻断同轮提案后的显式 keep，首次 keep 还会强读被放弃的结果。现先读取实际消费子集、按同一文本校验，封存后只允许合法待选方向的显式选择，原计划及结果不变；普通重复 finalize 仍拒绝。既有两个 keep 方法分别接同轮选择与首次缺放弃结果场景，保留原持久化及复用期待。 |
| IR3 | 三处 refine 说明改为清除 `cache.preflight`、保留原轮次和第一轮问题，与既有生命周期实际行为一致；无产品政策变更。 |
| IR4 | 两个 analyzer 明确全 reuse 也须执行零任务 resolve-finalize，封存空结果与复用身份。既有复用方法接空 resolve-finalize→普通 plan，检查可继续消费。定向复核又指出主 SKILL 的流水线仍有一句旧跳过指令，已同步为只跳过模型任务、仍执行空结果封存；该补正只改说明，测试结果继续适用。 |

本地执行工程师亲自执行以下定向命令，未新增测试方法或扩大业务目标：

```bash
uv run --no-project python -m unittest \
  test_stage2_analysis_level.TestLevelRefresh.test_preflight_reuses_a_legal_crlf_managed_file \
  test_stage2_resolved_direction.UserKeptProvisionalTests \
  test_stage2_analysis_level.TestResolvedConsumptionBoundary -v
```

结果为 4 项、2.656 秒、退出 0，全部通过；后一个既有方法复验 resolve 结果映射改动直接影响的候选漂移拒绝。版本、日志和退出码分别为 `implementation-review-version.txt`、`implementation-review-recheck.log`、`implementation-review-recheck.exit`，位于本记录开头的输出目录。定向重读两个入口的 6.1.5 C/D 与 6.3、主 SKILL 修订段，确认全复用仍收尾、同轮显式选择及修订失效说明一致。其余已执行结果未受影响，继续复用。

同一专用代理已对 `78a617a3e09919260fc84a81e8287c4c54226b9a`、主 SKILL 第 264 行补正及本记录完成定向复核，结论为“完整”：IR1–IR4 全部关闭，首次全部产物覆盖继续适用，未发现剩余实现缺项或待核实项。采用上述 4 项通过及未受影响的已有结果，未另跑测试。本地执行工程师确认产品和测试未再改变，后续提交只固定已审说明与本记录，按用户授权推送原 PR。

当前实现无未完成项；测试关口与合并判断交独立审核者负责。本记录及专用实现审核均不授予测试关口或合并批准。
