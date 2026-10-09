# 第66号议题／第73号拉取请求测试计划

版本：`issue-66-test-plan-new-rules-r4.15-2026-10-10`。

正式需求采用[第一关口第六版](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)，加验收决定人2026年10月9日删除“校验子代理最终消息与固定写入文件逐字节相同”要求的调整。实施依据为[第十六版完整执行计划](issue-66-implementation-plan.md)。目标分支基线为 `b19e53764ae654113140e3293e90ac49e9ff1d8f`，重基后的产品提交为 `f053d913afce47abed5abade9bf6e2737179f497`，A、C补充测试提交为 `162843c1c843989fbf09b45fd808d5276c92b94d`，校验代理文字修复为 `e6a4c19856c841f877fd082a5161cc083290156d`。

本版本删除R4.14新增的专用判定器、41项判定器预检、完整42项重跑、D组源文件与安装件重复检查和E组再次请求。历史运行、失败和批准记录保存在[测试计划审核记录](issue-66-test-plan-review.md)，不作为当前执行命令。

## 范围

- 正式状态是教授目录内的 `套磁候选状态.json`；本地候选稿是 `套磁想法候选.md`；总览是派生展示。
- 只检查第三阶段及直接改变的第四阶段读取入口。非 Codex 运行、同名消歧、断电或强制终止恢复、同教授并发写入和其他阶段改造不在本次范围内。
- 已有通过结果只有在被测行为、合同、依赖路径或夹具前提受到变化影响时才重跑。提交 SHA 变化本身不废除未受影响结果。
- 固定写入文件是唯一正式校验原文。带 `output_file` 的校验子代理最终消息只报告固定完成字段，不携带校验正文。
- `e6a4c19` 只恢复“最终唯一消息必须是一个 JSON object”的明示，没有改变写入、保存、记录、修正、停止或安装路径，因此不重开E组。

## 唯一必测清单

| 组 | 业务目标 | 证明方式 | 当前处理 |
| --- | --- | --- | --- |
| A | 当前教授独立提交、两文件失败恢复、候选稿冲突保护、第四阶段只读取指定教授 | 保存与读取入口的确定性测试 | R4.12三项当前结果通过，其余结果复用 |
| B | 正式状态稳定重建总览；错误时不发布部分内容；旧身份兼容准确 | 重建与兼容入口测试 | 仅重跑修正后的总览业务行比较方法 |
| C | 凭据固定输入；修正只处理点名对象；保留无关候选；最多两轮；`selected` 只读取明确传入的教授本地选择 | 计划、提交、准备和记录入口测试 | R4.12三项当前结果通过，其余结果复用 |
| D | 固定写入、保存和记录传递同一校验对象；错误不推进状态；临时交接字段不进入正式状态 | 写入、保存、记录及状态测试 | 仅重跑扩大递归字段检查的方法，其余结果复用 |
| E | 根对话和命名子代理按实际结果生成、校验、修正或停止，终态后重建总览 | 受支持安装与一次真实运行 | 复用R4.11结果，不发送新请求 |

## 结果复用依据

### A与C

R4.12在产品提交 `f053d913afce47abed5abade9bf6e2737179f497`、测试提交 `162843c1c843989fbf09b45fd808d5276c92b94d` 上运行六项受影响测试，结果为 `Ran 6 tests in 5.703s`、`OK`、退出码0。后续变化没有修改这些产品入口或断言，结果继续适用。

A组确认第四阶段按方向读取指定教授。C组确认项目级旧选择存在时，缺少教授本地 `--selection` 的计划和提交调用都以 `invalid_params` 拒绝且不写文件；明确传入教授本地选择后只处理所选方向并保留未选方向。

### B

现有B组结果继续适用。当前只修改 `test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection` 的断言：排除每次渲染都会变化的时间行后，比较全部稳定业务行。产品入口和业务预期没有变化，因此只运行该方法确认修正后的测试能够正确判断现有行为。

### D

现有D组结果继续适用。当前只修改 `test_record_validation_returns_input_bytes_sha` 的断言：从只检查一个位置扩大为递归检查正式状态中不存在 `invocation_file`、`handoff_file`、`handoff_sha256` 和 `validation_input_sha256`。产品入口和正式状态约定没有变化，因此只运行该方法。

`e6a4c19` 的单消息 JSON 明示由既有 `EarlyMachineOutputGateTests.test_every_json_agent_front_loads_single_message_protocol` 直接检查。固定完成报告、固定写入、保存和记录合同未变，既有D组源文件与安装件结果不重复执行。

### E

R4.11在固定产品提交 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d` 上完成受支持安装和唯一一次正式请求。安装件合同3项通过；请求返回HTTP 200、运行退出码0、`termination_reason=completed`，包含4个正式子线程。第一轮记录失败并只触发一次修正，第二轮记录 `pass_with_minor` 并停止；两轮固定写入、保存、摘要绑定和完成报告符合合同；终态后只重建一次总览。流程结果通过，内容结果为 `pass_with_minor`。

后续 `e6a4c19` 只补回等价文字明示。固定完成报告字段、文件入口、根消费路径和两轮停止条件均未改变，因此R4.11结果继续适用。当前不安装新消费者，不发送模型请求，也不创建新的事件判定程序。

## 当前唯一执行步骤

正式执行前记录计划版本、产品提交和测试提交；三者与第三关审核对象不一致时停止。只执行下面两个受影响方法：

```sh
set -eu
set -o pipefail
run_dir=$(mktemp -d /private/tmp/issue66-pr73-r415.XXXXXX)
printf '%s\n' 'issue-66-test-plan-new-rules-r4.15-2026-10-10' > "$run_dir/plan-version.txt"
git rev-parse HEAD > "$run_dir/tested-sha.txt"
cd .apm/skills/professor-contact/tests
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -m unittest -v \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection \
  test_issue66_r12_validation_input_sha.Issue66RecordValidationInputShaTests.test_record_validation_returns_input_bytes_sha \
  2>&1 | tee "$run_dir/affected-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/affected-tests.exit"
test "$test_exit" -eq 0
```

通过条件为精确收集并运行2项、两项均通过、退出码0。命令启动失败、测试无法收集或版本证据缺失记为未执行或证据不足；断言正常运行后失败才记对应业务检查失败。不得扩大到完整42项，不得重复运行D组合同检查，不得发送E组请求。

## 当前状态

- A、C：R4.12六项结果继续适用。
- B、D：2026年10月10日按当前唯一步骤运行2项，输出为 `Ran 2 tests in 2.894s`、`OK`、退出码0；记录目录为 `/private/tmp/issue66-pr73-r415.TF3qu0`。测试源码对应 `636f4bd556bbaacd5448725614eaeb108d5bbd95`，当前未提交变化只删除无关专用测试设施并修改计划文档，不改变这两个方法或产品入口。
- E：R4.11流程结果继续适用，内容结果为 `pass_with_minor`。
- 第二关须审核本版本的两项执行范围和复用依据；第三关再审核实际提交、日志、退出码和结果。本计划不自行批准第三关或合并。
