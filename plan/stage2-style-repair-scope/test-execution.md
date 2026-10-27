# TP1.1 执行记录

执行者：audit_validator_repair_coverage（测试编写/执行；不自授 Gate3 或合并批准）。
环境：dot 云端 Linux，Python 3.12.14；上游基线 a67ca3b630e00941d8c72ad7328a8f7796bda77b。
Gate2：独立 reviewer 在执行前批准 TP1.1，见 review.md。

## 第一次执行：2026-10-27
准确命令：TP1.1 recipe。日志 `/tmp/contact-style-scope.Cp156o/unittest.log`，备份 `/workspace/shared/contact-style-scope-first-run.log`。
结果：exit=1，21 tests / 84.411s，18 通过、3 失败，不宣称整体通过。

1. `test_old_scope_less_record_is_archived_once_on_normal_upgrade`：正常 finalize 返回 validation_render_stale，定位为测试模拟旧 display/ownership 后未更新 validator.pack_sha256，导致不自洽陈旧绑定。产品拒绝正确；仅在 fixture 按现有 fingerprint 绑定合法旧 pack，不放宽产品保护。
2. `test_source_and_label_style_reports_are_rejected_without_writes` 的中译子例：fixture 一行两次“中译：”，先触发 validation_quote_ambiguous。仅将 quote 改为唯一“- 中译：”，保留预期 scope 拒收及零写断言。
3. `test_u1_d_narrative_two_rounds_and_fixed_stop`：第二套 pending_env 仍使用纯固定标签的文风报告，被新 scope 拒绝。与该方法第一套一致，将模拟结构 owner 报告标为 C9，保留终态、owner、轮次断言。

独立 reviewer 已确认第2/3项为测试接线修正；迁移及正式 caller 修正后，仅对受影响目标复验，等待 Gate2 定向批准。不因文档提交重跑。

## 第二次执行：仅三项受影响方法

依据独立 Gate2 定向批准，采用同一隔离 recipe，选择器见 review.md。日志 `/tmp/contact-style-scope.OZNIRF/unittest.log`。exit=1，3 tests / 18.993s，2通过、1失败。

迁移测试已通过旧scope归档、正文/cache不变、新scope重检及正常再次刷新，最后比较整个 validator 时失败：既有 finalize 会为新接受元数据重算 pack_sha256，而测试误要求摘要本身不变。仅调整 fixture 断言：先验证新 binding 等于当前 pack fingerprint，再要求其余完整 validator 和历史数量不变。不修改产品保护；仅此方法等待独立批准复验。

## 第三次执行：仅迁移方法

依据独立 Gate2 单项批准，采用同一隔离 recipe。日志 `/tmp/contact-style-scope.bHDzRu/unittest.log`。exit=0，1 test / 4.984s，OK。

合并有效覆盖：首轮18项 + 第二轮2项 + 第三轮1项 = 原定21项全部获得成功结果（不是谎称单次21/21）。没有产品阈值/保护调整；失败和修正因果完整保留。TP目标5 caller/validator/SKILL 接线由独立普通合并审核只读核对；没有真实模型/外部服务运行。Gate3结论由独立reviewer给出。
