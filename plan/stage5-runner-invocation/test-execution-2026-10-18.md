# 第二批：Stage 5 审计来源改造 测试执行记录（2026-10-18）

- 测试计划：[test-plan.md](test-plan.md)，第 3 版（第一、二关口 PASS，第三关口 PASS）。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（`Plan conclusion: APPROVED`）。
- 被测提交：`ad674f2c265380de54c997e1fe04ef192aeab3af`；执行时 `git status --porcelain` 为空。
- 环境：本地 macOS，Python 3.14.7；未新增依赖、未新增判定器或采集器。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-batch2-*/`；本文件只记录命令、结果与必要片段。

## 执行命令与结果

在 `.apm/skills/professor-contact/tests` 下执行：

```sh
python3 -m unittest test_stage5_immutable test_stage5_fixture_isolation test_stage5_dualtarget_contract -v
```

结果：`Ran 26 tests in 36.998s`，`OK`，退出码 0；无 `FAIL` / `ERROR` / `skipped`。三个测试文件的用例数为 10 + 2 + 14 = 26，与日志逐条一致。

## 逐项结果

| 编号 | 结果 | 检查入口（日志中逐个 ok） |
| --- | --- | --- |
| T1 | 通过 | `TestStage5ImmutableTemplates.test_finalize_without_full_body_humanizer_preserves_fixed_segments`、`test_dynamic_field_polish_provenance_is_explicit`、`test_first_and_followup_are_both_rendered_from_stable_templates` |
| T2 | 通过 | `TestStage5AuditProvenanceInput.test_direct_runner_keeps_the_legacy_business_audit_label` |
| T3 | 通过 | `TestWrapperKeepsInstalledLayoutLocator.test_changed_audit_marker_fails_closed_before_writing_user_files`：断言非 0 退出、既有失败 JSON、且教授目录没有 md/txt/state。该用例不看“整个程序根零写入”：plan 阶段按既有契约可能已触发上游证据重建并写 `<program_root>/教授研究/_联系方式证据.json` |
| T4 | 通过 | `TestStage5AuditProvenanceInput.test_caller_supplied_internal_audit_option_never_decides_the_label` |
| T5 | 通过 | `TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker` |
| T6 | 通过 | `TestStage5ImmutableTargetedScope.test_issue59_t59_6_wrapper_finalize_keeps_selected_email_scope`、`test_stage5_fixture_isolation` 的两个用例、`TestStage5DualTargetContractTests.test_generator_wrapper_instructions_reject_full_body_inputs`、`test_issue59_t59_7_targeted_scope_documents_hold_selected_output_scope` |

## 清单入口与执行日志的对应

测试计划第 5 版把本批的本地通过条件收窄为清单已引用的 11 个入口（T1 三项、T2–T5 各一项、T6 四项）。这 11 项都包含在上面记录的模块级运行（26 项、`OK`）里：日志中逐个 `... ok` 的行即可对号。多出的 15 项来自三个模块的其余用例（生成器运行环境分支、`choices` 公开字段、校验器名称与网络权限等旧合同检查），它们是本批的清单外检查，**不构成本批的通过条件**，也不要求删除对应测试文件。

## 首次尝试记录（保留，不覆盖）

- 首次执行同一命令：26 项中 1 项失败，退出码 1。失败项为 T2 的新用例 `test_direct_runner_keeps_the_legacy_business_audit_label`，runner 返回 `result_missing`（`humanized body file required (--humanized)`）。
- 判定为**测试资产缺陷**而非产品缺陷：新用例当时没有按 `stage5-finalize` 的既有调用形状提供 `--humanized-map`；该要求在 `scripts/contact_state.py` 里，且不在本批改动范围内（本批只改渲染后缀、新增隐藏参数与解析器），wrapper 支持路径始终传映射。
- 修正只补齐必需输入：用例仍是真实 runner 直调（未换成 wrapper），断言未放宽。修正后先专项复跑（两个新增用例 OK），再整体重跑上表命令（26 项 OK）。日志：`targeted.log`（首次失败）、`t2.log`（专项复跑）、`targeted-r2.log` 与 `targeted-final.log`（整体重跑）。
- 最终整体重跑发生在提交之后，`sha.txt` 记录同一提交，满足“被测内容与推送内容一致”。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在 PR #97 的该提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`：运行 `39136220794` 成功（8m11s），检查项 `test` 为 pass。
- 按 `Test Engineer Rule.md` 第 6 节，本批不在本地重复全仓回归，直接采用该 CI 结果。

## 结论与交接

- 第三关口：T1–T6 对当前版本 `ad674f2c` 全部取得有效通过结果；无未完成项、无需要复验的项。
- 本记录之后如只改动文档（计划、记录、说明），未改产品代码与测试代码时，上述逐项结果继续有效并沿用。
- 下一负责人：合并审核（按 `Merge Reviewer Rule.md`），本记录不代替合并批准。
