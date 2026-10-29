# EP1 / TP1 定向执行记录

- 日期：2026-10-29；Python 3.12.14；云端 Linux，未接触 Mac。
- 基线：ad096fe31a4b5694cbe47a40f37b621435e1eeec。
- 候选：包含本记录的 `feat/email-analysis-links` 首个实现提交；测试时工作树产品/测试 diff 与该提交一致，后续仅补本记录。
- 独立 EP1 P1–P4 APPROVED、TP1 G1/G2 PASS 后实施；本记录只陈述运行结果，独立 reviewer 已核对候选 `1834ffdd8e9dc1d027db0d30a204f5993cb32633` 源码 M1–M3，无缺陷；TP1 G3 PASS。本次仅补审核状态，不重跑。

## 唯一执行尝试

仓库 tests 目录命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v \
  test_email_analysis_links \
  test_contact_state.TestStage5.test_stage5_email_analysis_links_are_md_only
```

完整日志：`/tmp/contact-email-analysis-links.lR1MgE/tests.log`；基线及产品 diff 同目录 `revision.txt` / `candidate.diff`（新增测试正文在本提交；diff 文件不包含未追踪文件）。

```text
test_audit_links_and_legacy_records ... ok
test_compile_freezes_canonical_paths_and_hash ... ok
test_stage5_email_analysis_links_are_md_only ... ok
Ran 3 tests in 2.087s
OK
exit_code=0
```

T1 覆盖不同 paper/gap canonical 路径、拒绝模型路径覆盖、缺字段及 hash 改变；T2 覆盖来源表、无 gap 支撑论文、gap-only later 来源、事实卡、含空格中日文相对链接及旧包无分析字段；T3 通过既有真实 CLI fixture 检查最终 md 内审和原 draft/txt 相等边界。

未运行全仓测试、安装、模型服务或真实教授任务。Mac 阅读器点击及用户真实路径可达性未实测。额外执行 `git diff --check` 无输出、退出 0，仅作补丁格式检查。
