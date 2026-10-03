# 第74号议题第三版测试审核与执行结果

本记录发布既有审核和执行结果，不修订测试方案或验收条件。唯一权威方案仍为 `issue74-test-r3`，提交 `df2e23a4cf13d2c477030eb71b24acc9f736dfb1` 的 `test-plan/issue-74.md` 及其指定文件；第三版全部取代第二版 `589ea76e5f9fb621848439ce965e7fe86a8d83e2`。

## 输入和审核来源

- 正式需求：[第74号议题需求第1版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，R1—R4，读取更新时间 `2026-10-02T16:02:24Z`。
- 冻结验收：该需求及第三版批准计划的兼容、写入保护、目录占用和归属清理约定；未增加产品要求。
- 计划：[第三版文件](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)，批准保留来源[评论5965870539](https://github.com/ScholarWorkflow/professor-contact/pull/76#issuecomment-5965870539)，读取更新时间 `2026-10-03T05:16:17Z`。
- 实现：`74034af796986584eaee05ad23e20e1c84b50240`；兼容基准 `768b49ef4514e36edec6b57ed3821a99af9e9c00`。测试使用的组合提交 `df2e23a4cf13d2c477030eb71b24acc9f736dfb1` 只加入计划与测试材料，运行模块、产品说明、实现测试与实现提交相同。
- 判定程序：最后修改提交 `f7917830d34f7b107f757cf2b6a476cc752631ab`，文件对象 `c81c9d481a36e4e9da44cfeeacbe9fcc0a189623`。
- 正式规范：项目共识优先于测试工程规则，完整读取版本的SHA-256分别为 `c49b52e5837a1a57bf16211e57a1bacdd7057a3d65efc6d2cb7bd523182e4b29`、`8c76bfc4db5108fe760f9eb0b2d9f6a44d9034ff96bd8f94614b6273b2aec944`。

对象为第二关口设计及第三关口执行。此前第二关口未完整通过；本次为首次完整通过前的修订审核，不适用通过后重开。第一关口需求与批准计划未变，保留完整通过。

已读材料包括上述完整需求、计划、正式规范、前两版正式审核记录、第三版全文与配套测试／编号／判定文件、完整迁移源码与说明、旧53／55业务测试、判定通道测试及原始结构化证据。必要依据无缺失，未消解来源冲突无。

## 修正与第二关口

两项均为测试程序问题：M1清单创建经 `os.open`，旧 `Path.open` 钩子未到达，导致竞争证明无效；M2路径保护读取共用模块的 `producer_root`，旧入口包装函数替换未被消费，导致合法外部路径被错误期待拒绝。最小修正分别为实际创建边界竞争注入、入口实际加载模块的虚构生产者前提；只影响R3对应两个方法及相邻观察检查。

最小检查先复现问题再修正，最终 `test/test_issue74_recipe_observers.py` 四方法确认实际保护和创建操作可观察，并拒绝覆盖竞争文件或取消生产者保护的错误实现。它们只调用最小文件操作，不执行完整准备业务。修正前、修正后及最终检查的全部本地原始尝试均保留；最终四方法检查的脱敏副本为 `evidence/issue-74/observers.json`，不是产品通过来源。

第3.3节八项均确认：唯一完整方案、每项必要证明有负责者、步骤可原样执行、当前可执行／隔离／可观察／可区分依据、失效检查删除、三个判定通道验证、无未声明状态参与、结果可由固定字段唯一判定。完整性不是只检查M1／M2。测试设计首次完整通过先于正式回归形成。

未变化的四方法判定检查、四方法异常边界检查及六个完整性样例复用第二版准确来源；判定入口、异常处理、39编号及通过检查均未改，修正不命中这些验证前提。脱敏记录分别见 `evidence/issue-74/evaluator-checks.json`、`recipe-checks.json`、`completeness-samples.json`、`completeness-results.json`。旧偏离尝试不复用产品结果。

`Test Engineer Gate 2: PASS`；`Gate review completeness: COMPLETE`。

## 一次正式回归与静态证明

运行编号 `issue74-evidence.uiCE2ET6`，开始 `2026-10-03T06:08:35Z`，结束 `2026-10-03T06:11:47Z`。产品／方案均为上述组合提交，CPython3.12.13、uv0.12.11。仓库检出运行前后干净。独占系统临时目录作为 `TMPDIR`，其中 `uv-cache`作为 `UV_CACHE_DIR`，设置 `PYTHONDONTWRITEBYTECODE=1`。不依赖共享运行资产、真实用户状态或外部服务，不修补消费者。

严格采用第三版的 `ABSOLUTE_PASS` 和一次G74，未重试、未另定向重复业务测试：

```sh
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern 'test_*.py' --require-prefix test_issue74_fixture_support.Issue74FixtureTests. --require-prefix test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests. --require-prefix test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests. --require-prefix test_gate2_evidence.Gate2EvidenceTests. --out "$RUN_DIR/regression.json"
jq --slurpfile required test-plan/issue-74-required-cases.json -f test-plan/issue-74-pass-check.jq "$RUN_DIR/regression.json"
```

退出码0；898方法有效开始并完成，编号唯一、顺序一致；全部事件、错误、失败、跳过、缺少前缀为空，无载入错误和中断。完整通过检查为 `true`。39必需编号均存在，分别为新增11、既有53号8、55号16、判定4；每个方法无失败／无效／跳过事件，原断言成立，因此每个为 `PASS`。

机器证据见 `evidence/issue-74/regression.json`，保留全部898方法及判定字段，只删除个人工作目录字段。它是既有运行的脱敏副本，不是新执行；完整原始响应和输出仍在本地保留。每个方法的版本、命令、运行编号及证据来源共用本节；所有方法第三关口行动为 `EXECUTE_CURRENT`，原因是迁移后没有获审方案下的可审核历史产品通过。产品历史通过复用／重新判定：无。

原始回归JSON摘要：`a23114cac1701968ac587d71b4352fc911f1343be80d8b2feb23b84d9a0647b2`。请求旧摘要的16失败未在本次出现，未取得其完整原始条件，不推断旧失败原因或宣称已修复。

S74完整源码与文档检查均满足：共用模块只负责目录／文件／摘要；53入口第104—126、128—144、159行和55入口第123—156、173行实际调用共用操作；业务虚构数据留在调用方；占用冲突、所有权、拒绝接管及回滚由共用第50—201行和53入口第90—102行负责；业务脚本、其他议题断言、状态接口和代理配置未改。固定说明路径 `.apm/skills/professor-contact/tests/README.md` 第5—74行覆盖分工、旧入口、新增样例、结构化判定、目录独立与异常清理责任。准确完整源码由测试提交追溯，不以关键词或作者摘要代替判断。S74为本次静态 `PASS`，不重复业务调用。

## 最终结果和记录发布影响

第一关口：`PASS`，完整。第二关口：`PASS`，完整。第三关口：`PASS`，完整；`Merge conclusion: READY`。M1／M2已修正确认；未解决缺陷、必须修改项、缺失当前关键证据、未审必需范围均无。

本次发布只新增结果记录和脱敏证据；测试实现、方案、输入、判定、产品及运行配置均未变。每个当前通过对发布后的版本仍有效；仅新增记录提交标识不重开关口或触发重复回归。通过来源仍是上述一次实际执行，不改写为发布提交的新执行。合并操作另行授权，本记录不执行合并。
