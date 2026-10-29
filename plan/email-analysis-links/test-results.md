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

## 发布后 CI 接入修正

首次 PR CI run 40867568727 在既有 `check_test_shards.py` 失败：新模块 `test_email_analysis_links` 未登记，业务 shard 尚未执行。这是本次测试接入遗漏，不归因环境或上游。最小将该模块登记到现有 shard3（mixed:stage4+stage5；2 个既有用例），不新增 shard、不改产品/业务测试、不重跑 G3。随后仅运行既有清单检查并记录其输出；历史测时聚合为原有快照，未伪造本模块独立测时。

清单检查实际输出：`OK: 89 test modules across 4 shards, each with a stage`，退出码 0。

## CI 暴露的旧断言同步

CI run 40868148684 清单检查全通过，shard2/3/4 成功；shard1 唯一失败为旧 `test_10_email_pack_self_contained` 对整个包禁止「论文分析」，与 R1 已批准透传真实分析路径矛盾。未归因上游/环境，未改变产品。独立 reviewer 已批准替换为按 item_key 对 canonical analysis_file 精确断言，并保留 future_work.json/_index.json 禁引用及 quote/page/status 自包含断言。

仅执行批准的受影响单例：`PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_contact_state.TestRunnerBasics.test_10_email_pack_self_contained`。日志 `/tmp/contact-email-analysis-compat.QXqE6l/tests.log`，实际 `Ran 1 test in 1.575s / OK / exit_code=0`。未重跑未改变的 T1–T3。

独立定向 G3 PASS：reviewer 已读取上述单例原始日志并确认与记录一致，原 T1–T3 结果继续有效。
