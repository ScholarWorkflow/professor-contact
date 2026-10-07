# Issue 68 第33版传递目录评估预检执行记录

本记录依照第28版测试计划第58–68、74–95段，记录一次真实请求、原判定和对完整原始证据的离线重新判读。它不代表正式验收，也不改变正式入口或通过条件。

## 结论

原判定器记录的终态为 `INVALID_TEST_EXECUTION`。修正事件分类后，按测试规则第3.3节对同一完整请求、响应和完整性证据执行 `REJUDGE_PRIOR_EVIDENCE`，离线重新判读为 `PASS`。原始 `preflight-result.json` 和响应均未改写，也未发送新请求。标记命令以退出码 `0` 完成创建、读取并核对、删除和确认不存在；请求前后选定目录的完整快照均为空，评估服务及干净消费者均未变化。第二关口仍为 `INCOMPLETE`，没有启动正式 `PC68-R1`。

原运行器把普通根代理消息事件 `agentMessage` 当作了委派证据，因此原始输出记为无效。修正后对完整原始响应离线运行新判定器，并用同一来源函数核对服务、消费者及目录前后快照；请求与响应摘要也与原记录相符，重新判读结果为 `PASS`。初次原判定和完整响应继续保留，未改写原始执行文件，也没有重复发送请求。第二关口仍待审核。

## 尝试记录

首次前置检查在干净消费者安装阶段失败，状态为 `CASE_NOT_STARTED`，原因是获取 GitHub 依赖时安全传输层连接中断；请求未发送。随后只读连通性诊断成功取得 `ScholarWorkflow/zotero-tools` 的 `HEAD`，据此继续了尚未完成的安装前置步骤，并使用新的消费者和独占临时目录。

第二次尝试通过受支持的 `apm install` 建立干净消费者，随后只发送了一次 `/eval` 请求。请求要求使用 `gpt-6-luna`、`low` 推理强度和 `workspace-write` 沙箱；服务记录的有效沙箱为 `workspaceWrite`，网络关闭。服务没有公开有效模型，因此记录只确认请求模型，不声称服务实际采用该模型。原判定结果为 `INVALID_TEST_EXECUTION`；更正判定器后，根据完整原始证据离线重新判读为 `PASS`，不是第二次运行。

原始请求摘要为 `88283d916a7af0b61bb20e4eb7459ab3ad989e262e005834514000445a5665cc`，响应摘要为 `92fff452afbeddfaea2c530a8a664730aedec3e9a580325ab6c8233286ceb403`。根线程运行代次为 `1`；标记命令在事件序号 `23435` 开始、`23436` 完成。响应中有57条普通根代理消息事件，没有 `collabAgentToolCall`、`subAgentActivity` 或线程关系。原运行器在序号 `23406` 的 `agentMessage` 事件上产生了无效终态。

首次失败及第二次尝试的原始响应、安装日志、服务前后来源记录和完整目录快照均保存在本机临时证据目录，公开记录只保存摘要与占位符，不提交原始响应或本机绝对路径。摘要见[机器可读证据](../tests/runtime/evidence/issue68-r33-transfer-location-eval-preflight.json)。

## 判定修正与验证

原识别逻辑把任何包含“agent”的事件类型都视作委派，因而将正常的 `agentMessage` 错判为代理活动。修正后只拒绝 `collabAgentToolCall`、`subAgentActivity`、明确委派标记、非空线程关系及非根线程事件；普通根线程回复不再触发该判定。随后依测试规则第3.3节，仅因判定解释变化且完整原始证据包含所需事实，对保存的请求、响应及完整性快照执行 `REJUDGE_PRIOR_EVIDENCE`。重判结果为 `PASS`；请求和响应摘要匹配，服务与消费者未变化，前后目录快照完整、同根且为空。原始运行结果文件仍保留旧判定 `INVALID_TEST_EXECUTION`，机器证据同时记录原判定和离线重判；没有重复请求。

定向验证命令：

```sh
UV_CACHE_DIR="$ISSUE68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_issue68_transfer_location*.py'
```

结果为31项通过；预检入口帮助检查退出码为0。覆盖项包括完整标记链、权限阻断、身份类型冲突、额外命令、子线程、正式委派事件形状、普通代理回复、快照消失和目录隔离条件。

离线重判摘要可用 `jq` 查看机器证据的 `initial_preflight_state`、`final_preflight_state`、`offline_rejudgment` 和第二关口状态。离线判定使用修正后运行器中的 `verify_probe`、`runner.same_service` 与 `snapshots_are_complete_empty_same_root`；它只读取本机已保存文件，不调用评估服务，也不覆盖原始结果。

## 复执行步骤与终态处理

运行位置为包含本记录和预检程序的测试仓库根目录；先在三个已准备的本地检出目录中解析来源根路径，路径只保存在当前 shell。产品检出须固定在 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，共享夹具检出须固定在 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，评估服务检出须固定在 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 并使用其 `direnv` 环境；三者均须干净。`PC68_PRODUCT_CHECKOUT`、`PC68_SHARED_CHECKOUT` 和 `PC68_EVAL_CHECKOUT` 是本机已准备好的检出目录输入，不写入公开证据。运行下列准备命令时，当前目录必须是测试仓库根目录：

```sh
PC68_TEST_ROOT="$(pwd -P)"
: "${PC68_PRODUCT_CHECKOUT:?设置为已固定版本的产品检出目录}"
: "${PC68_SHARED_CHECKOUT:?设置为已固定版本的共享夹具检出目录}"
: "${PC68_EVAL_CHECKOUT:?设置为已固定版本的评估服务检出目录}"
PC68_PRODUCT_ROOT="$(cd "$PC68_PRODUCT_CHECKOUT" && pwd -P)"
PC68_SHARED_ROOT="$(cd "$PC68_SHARED_CHECKOUT" && pwd -P)"
PC68_EVAL_ROOT="$(cd "$PC68_EVAL_CHECKOUT" && pwd -P)"
test "$(git -C "$PC68_PRODUCT_ROOT" rev-parse HEAD)" = "b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d"
test -z "$(git -C "$PC68_PRODUCT_ROOT" status --porcelain)"
test "$(git -C "$PC68_SHARED_ROOT" rev-parse HEAD)" = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
test -z "$(git -C "$PC68_SHARED_ROOT" status --porcelain)"
test "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" rev-parse HEAD)" = "3fdfa9387140cfc2e2aa3af415f85015f79706d2"
test -z "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" status --porcelain)"

umask 077
PC68_R33_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r33-transfer-eval-preflight-XXXXXX)"
mkdir "$PC68_R33_RUN_ROOT/transfer"
PC68_TRANSFER_ROOT="$PC68_R33_RUN_ROOT/transfer"
test -z "$(ls -A "$PC68_TRANSFER_ROOT")"
test "$(ls -A "$PC68_R33_RUN_ROOT")" = "transfer"
test ! -e "$PC68_R33_RUN_ROOT/evidence"
uv run --no-project python "$PC68_TEST_ROOT/.apm/skills/professor-contact/tests/runtime/preflight_issue68_transfer_location_eval_r33.py" \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --transfer-root "$PC68_TRANSFER_ROOT" \
  --output-dir "$PC68_R33_RUN_ROOT/evidence"
```

五个程序参数依次来自已核对版本的产品检出、共享夹具检出、评估服务 `direnv` 检出、新建运行目录中的空 `transfer/`，以及同一运行目录下尚不存在的 `evidence/`。输出目录由程序创建。读取结果时，不以进程退出码代替状态判定；退出码非零时仍检查已写出的结果文件：

```sh
jq '{state,reason,request_attempted,request_body_sha256,response_body_sha256,observation,integrity}' \
  "$PC68_R33_RUN_ROOT/evidence/preflight-result.json"
```

依第28版六类终态处理：`PASS` 仅表示本用例负责的事实均有有效证据，仍须经过第二关口审核才可决定后续工作；`FAIL`（历史机器标签 `FAIL_PRODUCT`）表示有效证据已证明产品违约；`BLOCKED` 表示执行开始后外部服务、模型、权限或受支持观察条件阻断判断；`NOT TESTED` 表示没有形成声明路径，且原因不是产品违规、外部阻断或测试缺陷；`INVALID_TEST_EXECUTION`（历史标签 `INVALID_EVIDENCE`）表示前提、执行或证据无效；`CASE_NOT_STARTED` 表示尚未越过启动边界。所有状态均保留原始输出。只有在请求未发送且前置条件经独立诊断恢复时，才可用全新消费者和新运行目录继续未完成的预检；请求已发送后不在相同条件下重试。此次请求仅发送一次：原始 `preflight-result.json` 状态为 `INVALID_TEST_EXECUTION`，之后按规则第3.3节离线重判为 `PASS`；没有覆盖原文件、没有重发请求，也没有启动正式 `PC68-R1`。第二关口保持 `INCOMPLETE`。

固定产品版本为 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，共享夹具仓库版本为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，评估服务版本为 `3fdfa9387140cfc2e2aa3af415f85015f79706d2`。服务隔离状态为 `ISOLATION_CONFIRMED`，请求前后服务和消费者均未变化。命令行参数与沙箱行为参考了[官方命令行示例](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)及[官方配置说明](https://developers.openai.com/zh-Hans/docs/config-file/config-basic)。
