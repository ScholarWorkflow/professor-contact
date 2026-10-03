# 第 74 号议题正式测试结果

## 输入版本

- 正式需求：Issue #74 需求第 1 版 R1–R4。
- 正式执行计划：计划第 4 版修订 1，语义提交 `07f895e3bfb91f2d27300042676aff5317d348cf`，已批准。
- 测试方案：`issue74-plan4-test-r2`。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 正式被测版本：`c757d8d1e61ff14db93164c67897530a278c15af`。
- 判定程序来源：`fcb5068570d8db5a4a0cbe89ae02c975da8c963d`。

## 正式执行

- GitHub Actions run：`37143439523`。
- workflow artifact：`issue74-formal-c757d8d1e61ff14db93164c67897530a278c15af`，artifact id `11281211672`，SHA-256 digest `9e1c8262df9b60040fb8459f837fd3fbe5a62e3a36368d1c9ac360b98feff477`。
- CPython：3.12.14。
- `jq`：1.7。
- Recipe SHA：`c757d8d1e61ff14db93164c67897530a278c15af`。
- 独立检出：准确 checkout 被测 SHA，执行前后干净。
- 重试：0。

六个 Case 均为本版 `EXECUTE_CURRENT`：

| Case | tests_run | started/completed | verdict | exit | failures | errors | skipped | missing prefix |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| T74-CORE | 16 | 16 / 16 | PASS | 0 | 0 | 0 | 0 | 0 |
| T74-CLI | 3 | 3 / 3 | PASS | 0 | 0 | 0 | 0 | 0 |
| T74-53 | 8 | 8 / 8 | PASS | 0 | 0 | 0 | 0 | 0 |
| T74-55 | 16 | 16 / 16 | PASS | 0 | 0 | 0 | 0 | 0 |
| T74-STATIC | 4 | 4 / 4 | PASS | 0 | 0 | 0 | 0 | 0 |
| T74-EVIDENCE | 4 | 4 / 4 | PASS | 0 | 0 | 0 | 0 | 0 |

全部结构化结果同时满足：`load_errors=[]`、`events=[]`、`interruption=null`。`T74-CLI` 的 `test_generated_bytes_hashes_and_returns_match_compatibility_base` 实际启动并完成，没有 skip；第 53、55 号当前构建结果与 `768b49e...` 基准在同一输入路径下返回对象、全部生成文件字节和摘要一致。

## 历史尝试与修订

- 本地执行容器在 Case 开始前缺少 CPython 3.12，只存在 3.13；未换解释器代跑，该尝试按 Recipe 记录为 `CASE_NOT_STARTED`，不作为产品失败。
- 第 1 版测试方案发现两项测试侧问题后被取代：普通浅克隆缺少基准对象会误报准备错误；R2 的生成文件字节兼容存在明确 `false-PASS`。当前第 2 版已分别通过正式前置基准检查与基准逐字节比较修正。
- 产品 `22a4db04...` 的前一正式运行也曾得到六 Case `PASS`，只作为修订过程证据；最终 Gate 3 只采用上表 `c757d8d...` 运行。

## 结果文件更新后的复用判断

本文件的最终填写发生在上述正式执行之后，因此仓库 HEAD 会只因 `test-plan/issue-74-results.md` 文本更新而变化。该变化不命中六个 Case 的复验依赖：产品实现、测试源码、Recipe、判定程序、兼容基准和执行环境约定均未变化；`T74-STATIC` 只检查变更文件路径集合，本结果文件在正式执行的 `c757d8d...` 中已经存在且已经列入允许路径，修改其正文不会改变该集合。因此六个 PASS 对只包含本结果文本更新的后续 HEAD 继续有效，记录为 `REUSE_PRIOR_PASS`。

## 第三关口

- Gate 1：冻结需求 R1–R4 无冲突，`PASS`。
- Gate 2：`issue74-plan4-test-r2` 完整证明设计，`PASS`，完整性 `COMPLETE`。
- Gate 3：六个必需 Case 对当前产品版本均有有效 PASS，`PASS`。
- 未解决 `PRODUCT`：无。
- 未解决 `RECIPE`：无。
- 必需 Case 的 `BLOCKED` / `NOT TESTED` / `INVALID_TEST_EXECUTION` / `CASE_NOT_STARTED`：无；前述本地环境尝试未作为最终执行来源。

`Test Engineer Gate 2: PASS`

`Gate 2 review completeness: COMPLETE`

`Gate 3: PASS`

`Gate 3 review completeness: COMPLETE`

`Merge support from test review: READY`
