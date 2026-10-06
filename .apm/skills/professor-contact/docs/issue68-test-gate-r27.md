# 第 72 号拉取请求：第 27 版测试实现与预检记录

记录版本：`issue68-r27-r24-preflight-2026-10-06`。

**状态：第二关口未完成，当前不能执行 PC68-R1。** 本记录绑定 PR #72 评论 [测试计划第24版](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6009207405)。本次完成的是已授权的本地判定器修正、拒绝启动保护和预检；逐次输入来源仍须由测试计划审核者确定。本记录不声称 Gate 2 或 Gate 3 通过。

## 1. 版本依据

| 项目 | 固定版本或状态 |
| --- | --- |
| 测试计划 | 第24版，PR #72 评论 `6009207405` |
| 批准的产品计划 | 第13版，产品提交 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 被测产品 | `ScholarWorkflow/professor-contact@b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 共享适配器 | `skills-test-fixtures@c738fa2f8bcbb16cd99d741332d5f59b062b6357`，adapter@16 |
| 运行证据契约 | `issue-68-runtime-evidence-r27-2026-10-06` |
| 当前测试代码 | `ScholarWorkflow/professor-contact@aea66fdafbd68f53def5cc39f55789f55f45d6c5`；判定器和入口仍使用 `r19` 文件名 |

第23版候选记录 [issue68-test-gate-r25.md](issue68-test-gate-r25.md) 已明确标为历史资料。它及其旧测试结果不再证明第24版要求。

## 2. 查明的输入证据缺口

当前 adapter@16 的 `app_server_events` 对 `commandExecution` 提供调用编号、命令、聚合输出、线程及事件顺序。它不提供每次调用实际交付或读取的输入字节。子线程的 `agent_message` 含加密内容；`child_thread_reads` 只有元数据。

因此，命令里的 JSON 或 Python 字面量、`--choices` 路径、调用结束后重新读取的临时文件、manifest 预期值及最终业务结果，都不能证明具体调用消费了什么。连续两次调用也必须各自有输入记录；仅有相同命令不能合并成一次证明。

当前仍没有可支持的逐次输入观察格式。本次没有自行增加或替换证据来源。以下事实尚不能区分：合法读取后清理、实际读取内容错配、必要观察缺失、证据损坏或归属冲突。

## 3. 已完成的本地实现

- `verify_issue68_stage5_routing_r19.py` 不再从命令文本提取业务对象。每个教授线程的业务调用继续保留各自 `commandExecution.id`；逐次输入证据缺失时按调用编号返回 `BLOCKED_OBSERVABILITY / owner_actual_input_unobservable`。
- `_plan_checks` 不再重开 `--choices` 路径。路径参数可见但调用读取时的内容不可见，因此该调用不能被判为输入正确；命令中明确观察到的错误 owner 或 `--choices-scope` 仍按产品失败处理。
- `run_issue68_stage5_routing_r19_codex.py` 在检查产品、fixture、评估服务和发送正式请求前写入 `input-evidence-preflight.json`。来源状态不受支持时，终态为 `CASE_NOT_STARTED / actual_input_evidence_source_unavailable`；不会进入服务检查或请求代码。
- 运行契约升至 r27，明确记录来源缺失、禁用的替代证据、逐次关联要求以及 Gate 2 未完成状态。
- `test_issue68_runtime_r19.py` 不再把命令字面量和事后文件内容当作可通过的消费证据，改为覆盖上述阻断、调用编号留存、文件不重读和正式入口早停。

## 4. 本地预检

执行命令：

```bash
env UV_CACHE_DIR=/private/tmp/uv-cache-pr72 uv run --no-project python \
  .apm/skills/professor-contact/tests/test_issue68_runtime_r19.py
```

结果：7 项通过，0 项失败。正式入口的预检用例确认 `clean_revision`、服务 provenance 检查及 `codex_host` 都未调用，并在临时输出目录留下 `CASE_NOT_STARTED` 终态和来源阻断记录。

本地预检只证明入口会拒绝缺少逐次输入记录的运行，不证明产品验收通过，也不证明未实现的错配、损坏或合法清理分类。

## 5. 关口与下一步

| 计划要求 | 当前结果 |
| --- | --- |
| 合法输入被读取，随后临时文件清理 | 没有受支持来源，未验证 |
| 有效输入证据证明本次读取与来源错配 | 没有受支持来源，未验证 |
| 必需输入观察缺失 | 已实现并验证为 `CASE_NOT_STARTED`，正式请求前停止 |
| 输入证据损坏或归属冲突 | 没有受支持来源，未验证；不能编造格式后声称通过 |
| 第二关口 | `INCOMPLETE` |
| PC68-R1 | 本次未运行；正式入口因预检来源不支持而拒绝启动 |
| PC68-D1 | 第24版不要求本轮重跑；历史尝试保留，不挪作 PC68-R1 输入证明 |
| 第三关口 | `NOT READY` |

测试计划审核者需确定受支持的逐次输入来源和调用关联办法。若来源由共享适配器或运行环境提供，应由相应负责人实现。来源需在临时文件清理后仍可复查，并覆盖合法输入、错配、缺失、损坏及归属冲突。来源确定后，测试实现需更新观察解析、证据契约和这四类预检，再由审核者指定单一完整候选；在此之前不得执行 PC68-R1。

## 6. 后台更新监视

继续使用本地轮询脚本 `.tmp_scripts/1006_pr72_watch.sh.tmp`，运行会话 `30970`，日志 `.tmp_scripts/1006_pr72_watch.log`。该脚本轮询 PR #72，有更新时记录并通知；未使用定时任务。
