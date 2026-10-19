# 边界四：证据快照与决策阶梯搬移 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 2 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（`Plan conclusion: APPROVED`）。
- 对照基准：`cdd01f7f2c03be822adbb5a4117c7e65a89d6c82`。
- 被测提交：`ec896e4`（改基到 `main`（已含 #98/#99/#100/#101）之后的同一实现提交；改基前依次为 `5f80206`、`8f6cc86`、`f527698`，四者引入的 `.apm/` 补丁逐字节相同——已用补丁哈希核对）；docstring 修复提交随其后。
- 环境：本地 macOS，Python 3.14.7；驱动只用标准库，比较用 `jq` 按键过滤。仓库 CI 使用工作流固定的 Python 3.12。
- 实现符合性审核（M2）指出计划步骤“更新模块 docstring”未落实（D1，非阻断）：已在实现提交后补上该 docstring 两处（标题句与注入面说明），并复跑验证——T1–T4 在 `base7.json`／`head7.json` 上仍逐字段相同（排除 `injection_sites`）、T5 `Ran 42 tests in 66.808s`、`OK`；docstring 不参与执行，产品行为未变。
- 原始输出（仓库外）：`/tmp/pc-bnd4-check/`；证据文件 `base4.json`／`head4.json`（最终对照，含 verdict 分支）与 `base3.json`／`head3.json`（补分支前的对照）、`ladder3.log`（T5 最终运行）、历史尝试 `base.json`／`head.json`（兄弟模块命名不对，基准侧导入失败）、`base2.json`／`head2.json`（artifact 取当前时间，`generated_at` 有假差异）、`ladder.log`／`ladder2.log`（缺 `datetime` 导入与 TTL 体引用的两次失败）。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | `base4.json` 与 `head4.json` 在排除 `injection_sites` 后逐字段相同：五种 artifact 与“无 artifact + 错误码”的返回字典相同；runner 侧 `contact_evidence_snapshot` 签名两侧都是 `(artifact, artifact_error, professor) -> dict | None`（`base3.json`／`head3.json` 是补 verdict 分支前的历史对照，只有 27 组） |
| T2 | 通过 | 同一对比，共 32 组：24 组状态矩阵（4 `state` × 3 `checker_error` × 2 `rebuild_ran`）、2 种 `artifact_error`、1 组 artifact 级 `degraded` 标志（结果 accept），以及 5 条 verdict 分支——`insufficient` → `contact_evidence_insufficient`、`current_email=None` → `contact_evidence_ambiguous`、`bogus` → `contact_evidence_invalid_record`、`paper_only` → `contact_evidence_paper_only`、`conflict` → `contact_evidence_conflict`；每组的完整决策对象逐字段相同 |
| T3 | 通过 | 同一对比：三条 email（含重复教授与无证据教授）的决策字典键集合与每个值相同 |
| T4 | 通过 | 同一对比：8 种时间输入（当天／29／30／31 天前／未来／`None`／非时间字符串／数字）的返回值逐项相同 |
| T5 | 通过 | `ladder3.log`：`Ran 42 tests in 55.801s`，`OK`，退出码 0（`test_contact_evidence_ladder` 40 项 + `test_stage5_fixture_isolation` 2 项） |
| 既有仓库检查 | 通过 | 补 docstring 后的重跑：运行 `39205685832`，6m30s，检查项 `test` pass（head `e655ddb`）。此前的运行：CI 在 head `f65dd7c` 上跑全量 `unittest discover`：运行 `39163647723`，5m38s，检查项 `test` pass。按测试计划第 22 行这项不属于本批业务必测项，只作既有检查结果引用；该 head 相对被测提交只多文档提交，`.apm/` 字节未变 |

## 执行方法与命令

1. 两侧同构目录 + 驱动复制（见测试计划第 1 步）；基准侧五个文件按原名写入 `$RUN/base/`，改动侧复制工作树的 `contact_state.py` 与全部 `_*.py` 到 `$RUN/head/`。
2. T1–T4：
   ```sh
   set -e
   uv run --no-project "$RUN/ladder_probe.py" "$RUN/base/contact_state.py" "$RUN/base-work4" > "$RUN/base4.json"
   uv run --no-project "$RUN/ladder_probe.py" "$RUN/head/contact_state.py" "$RUN/head-work4" > "$RUN/head4.json"
   jq 'del(.injection_sites)' "$RUN/base4.json" > "$RUN/base4.filtered.json"
   jq 'del(.injection_sites)' "$RUN/head4.json" > "$RUN/head4.filtered.json"
   diff -u "$RUN/base4.filtered.json" "$RUN/head4.filtered.json" && echo "T1-T4 IDENTICAL"
   jq -c '.injection_sites' "$RUN/head3.json"
   ```
   输出：`T1-T4 IDENTICAL (incl. verdict branches)`（最终一次运行用 `base4.json`／`head4.json`，含 5 条 verdict 分支）；注入点实测 `contact_evidence_record=["compact_name"]`、`contact_evidence_freshness_reason=["verify_ttl_days"]`、`_evaluate_record_ladder=["compact_name","sha256_obj","verify_ttl_days"]`，其余五个（含三个包装）为空数组，与执行计划一致。
3. T5：`python3 -m unittest test_contact_evidence_ladder test_stage5_fixture_isolation -v` → `Ran 42 tests`、`OK`。
4. 搬移核对：基准的 `197-199` 与 `8411-8675` 两段反向套用全部文档化改动后，与新模块正文逐字节相同。改动点共 **14 处**：6 处签名（`contact_evidence_record`／`contact_evidence_snapshot`／`contact_evidence_freshness_reason`／`evaluate_contact_evidence`／`_evaluate_record_ladder`／`contact_evidence_decisions`）、7 处内部调用（`contact_evidence_record` ×2、`contact_evidence_freshness_reason` ×1、`evaluate_contact_evidence` 内的 `_evaluate_record_ladder` ×2、`contact_evidence_decisions` 内的 `evaluate_contact_evidence` ×1 与 `professor_source_state` ×1）、1 处 TTL 体引用（`VERIFY_TTL_DAYS` → `verify_ttl_days`）。

## 执行中修正的问题（保留记录）

- 首次运行 32 项失败：模块缺 `from datetime import datetime, timedelta, timezone`（执行计划 P4 已提醒，实施脚本漏了）。补导入后仍失败 31 项。
- 第二次失败：`contact_evidence_freshness_reason` 的函数体仍引用全局 `VERIFY_TTL_DAYS`，注入参数没被真正使用（`NameError`）。把函数体改为 `timedelta(days=verify_ttl_days)`，即第 14 处文档化改动（6 处签名 + 7 处内部调用 + 1 处 TTL 体引用），之后 42 项全过。
- 探针自身的两次修正：① 基准副本与兄弟模块命名不匹配导致基准侧导入失败；② artifact 用当前时间生成，两侧 `generated_at` 相差数毫秒产生假差异，改为固定时间戳。
- 测试计划第 1 版审核指出阶梯的三条回落分支（`contact_evidence_insufficient`／`ambiguous`／`invalid_record`）在既有用例与矩阵里都没有被执行；驱动补了 5 条 verdict 分支案例（含 `paper_only` 与 `conflict`），两侧仍逐字段相同。
- 以上均为实施/测试资产问题，产品行为未变；失败运行与日志保留在 `/tmp/pc-bnd4-check/`。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果按运行编号与所跑 head 单独记录，按测试计划不属本批业务必测项。

## 结论与交接

- T1–T5 对被测提交取得有效通过结果；既有仓库检查待 PR 打开后补运行来源。
- 本记录之后如只改文档，未改产品与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批堆叠在边界三分支 `refactor-contact-evidence`（PR #101）之上，合并顺序 #98 → #99 → #100 → #101 → 本批。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
