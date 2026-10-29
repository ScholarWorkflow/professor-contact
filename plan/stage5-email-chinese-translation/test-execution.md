# TP1.1 离线执行记录

- 日期：2026-10-29；基线 `ad096fe31a4b5694cbe47a40f37b621435e1eeec` 加本 PR 工作 diff，分支 `feat/stage5-email-chinese-translation`。
- 云端 Python unittest，无模型调用、安装、Mac操作或用户材料；synthetic fixture 临时目录由既有 BaseEnv 管理。
- T1/T2：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage5_email_translation.py' -v`，最终精确收集 2 项、exit 0、OK。观察双 md 正确位置/独立译文、txt 精确等于 translation_source、模板字节保留；stale/missing中译及手改md拒绝后产物/状态不变。
- T3：`cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_immutable.TestStage5ImmutableTemplates.test_finalize_without_full_body_humanizer_preserves_fixed_segments -v`，1 项、exit 0、OK；包括新增无中文译文节断言。
- `git diff --check`：exit 0，无输出。
- 原始日志：`/tmp/stage5-email-translation-validation/T1-T2-targeted.log`、`T3.log`。
- 执行偏离保留：第一次新测试模块直接导入既有 TestCase，unittest 除 T1/T2 外额外收集 8 个既有 case，共 10 项 OK。原日志 `T1-T2.log` 保留。随后改为模块导入阻止无关收集，按原批准范围精确执行 2+1；额外执行不是新增验收义务，不要求重复。
- T4：未执行；当前无已确认正式 consumer/eval/fixture路径，真实模型翻译语义/agent接线不能以离线合成中文代替。整体测试与合并结论不作 PASS。
- 以上为执行者事实记录，待独立 Gate 3/代码复核。

## T2 定向修订复验
独立 reviewer 要求使用已有 parse(result) 检查真实 JSON status/reason_code，而非 stdout 子串匹配。已在原三个失败场景作此最小修订：stale/missing 为 error，手改为 needs_decision，并分别精确核对原因码。仅执行 `cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_email_translation.TestEmailTranslation.test_stale_missing_and_manual_changes_preserve_outputs -v`；1 项、exit 0、OK，日志 `/tmp/stage5-email-translation-validation/T2-structured.log`。T1/T3 产品行为未改，沿用既有结果；T4仍未执行。
