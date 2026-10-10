# 第66号议题／第73号拉取请求测试计划

版本：`issue-66-test-plan-new-rules-r4.16-2026-10-10`。

正式需求采用[第一关口第六版](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)，加验收决定人2026年10月9日删除“校验子代理最终消息与固定写入文件逐字节相同”要求的调整。实施依据为[第十六版完整执行计划](issue-66-implementation-plan.md)。目标分支基线为 `b19e53764ae654113140e3293e90ac49e9ff1d8f`；当前产品修改提交为 `47c58de235f8e18db1e8a2520c9fa80c6d145b0f`，它在 `c6b77e4c83acbe5f9be1e9b18b7f41f43154d498` 之后修改校验问题记录和修正范围读取，并加入两项初始回归测试。

R4.15删除R4.14新增的专用判定器、41项判定器预检、完整42项重跑、D组源文件与安装件重复检查和E组再次请求。R4.16保留该精简结果，只重开 `47c58de` 直接改变的C组修正范围。历史运行、失败和批准记录保存在[测试计划审核记录](issue-66-test-plan-review.md)，不作为当前执行命令。

## 范围

- 正式状态是教授目录内的 `套磁候选状态.json`；本地候选稿是 `套磁想法候选.md`；总览是派生展示。
- 只检查第三阶段及直接改变的第四阶段读取入口。非 Codex 运行、同名消歧、断电或强制终止恢复、同教授并发写入和其他阶段改造不在本次范围内。
- 已有通过结果只有在被测行为、合同、依赖路径或夹具前提受到变化影响时才重跑。提交 SHA 变化本身不废除未受影响结果。
- 固定写入文件是唯一正式校验原文。带 `output_file` 的校验子代理最终消息只报告固定完成字段，不携带校验正文。
- `47c58de` 只重开校验问题如何进入正式记录，以及修正入口如何读取已记录范围；不重开未受影响的本地提交、总览、交接字段和第四阶段读取结果。

## 唯一必测清单

| 组 | 业务目标 | 证明方式 | 当前处理 |
| --- | --- | --- | --- |
| A | 当前教授独立提交、两文件失败恢复、候选稿冲突保护、第四阶段只读取指定教授 | 保存与读取入口的确定性测试 | R4.12三项当前结果通过，其余结果复用 |
| B | 正式状态稳定重建总览；错误时不发布部分内容；旧身份兼容准确 | 重建与兼容入口测试 | 采用R4.15当前结果 |
| C | 凭据固定输入；文件级问题展开到全部实际渲染的方向和跨方向组；修正范围、问题正文和候选只取正式状态中已记录内容；保留无关对象；最多两轮；`selected` 只读取明确传入的教授本地选择 | 计划、提交、准备和记录入口测试 | 复用R4.12未受影响结果；补齐并运行两项当前修正检查 |
| D | 固定写入、保存和记录传递同一校验对象；错误不推进状态；临时交接字段不进入正式状态 | 写入、保存、记录及状态测试 | 采用R4.15当前结果，其余结果复用 |
| E | 根对话和命名子代理按实际结果生成、校验、修正或停止，终态后重建总览 | 受支持安装与一次真实运行 | 复用R4.11结果，不发送新请求 |

## 结果复用依据

### A与C的既有结果

R4.12在产品提交 `f053d913afce47abed5abade9bf6e2737179f497`、测试提交 `162843c1c843989fbf09b45fd808d5276c92b94d` 上运行六项受影响测试，结果为 `Ran 6 tests in 5.703s`、`OK`、退出码0。`47c58de` 没有改变A组行为、C组凭据身份、旧选择拒绝或显式选择行为，这些结果继续适用；它改变的C组修正范围由下一节单独检查。

A组确认第四阶段按方向读取指定教授。C组确认项目级旧选择存在时，缺少教授本地 `--selection` 的计划和提交调用都以 `invalid_params` 拒绝且不写文件；明确传入教授本地选择后只处理所选方向并保留未选方向。

### C组当前修正

`47c58de` 修改两项正式行为。第一，记录文件级阻断问题时，将问题展开到本次成品中实际渲染的全部方向和跨方向组，并把这些对象写入正式状态的 `validator.pending`。第二，后续校验文件即使被改写，`stage3-plan` 和 `stage3-finalize` 也只能采用 `validator.pending` 已记录的范围、问题正文和候选编号；改写文件新增或替换的内容不能进入修正任务。

本地测试工程师先修订 `Issue66RecordedValidationScopeTests` 中现有两项方法，再运行它们：

- `test_handoff_record_expands_global_blocker_to_rendered_objects`：输入至少包含一个普通方向和一个跨方向组，文件级阻断问题位于不归属单个对象的渲染文字；记录结果必须为 `needs_correction=true`、`terminal=false`，返回范围和 `validator.pending` 必须恰好包含全部实际渲染对象，每个对象都保留该问题。
- `test_rewritten_validation_file_cannot_expand_or_replace_recorded_correction`：先记录一个方向的问题，再把保存后的校验文件改成替换原问题并增加另一方向问题；`stage3-plan` 必须成功，且任务只含已记录方向、原问题正文和原候选编号；`stage3-finalize` 必须成功，只替换已记录对象，并保持未涉及方向、跨方向组和校验记录不变。任一入口返回错误均为失败，不能作为允许结果。

这两项检查直接使用现有测试框架和产品入口，不新增专用判定器，也不重复A—D其他结果。

### B

现有B组结果继续适用。当前只修改 `test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection` 的断言：排除每次渲染都会变化的时间行后，比较全部稳定业务行。产品入口和业务预期没有变化，因此只运行该方法确认修正后的测试能够正确判断现有行为。

### D

现有D组结果继续适用。当前只修改 `test_record_validation_returns_input_bytes_sha` 的断言：从只检查一个位置扩大为递归检查正式状态中不存在 `invocation_file`、`handoff_file`、`handoff_sha256` 和 `validation_input_sha256`。产品入口和正式状态约定没有变化，因此只运行该方法。

`e6a4c19` 的单消息 JSON 明示由既有 `EarlyMachineOutputGateTests.test_every_json_agent_front_loads_single_message_protocol` 直接检查。固定完成报告、固定写入、保存和记录合同未变，既有D组源文件与安装件结果不重复执行。

### E

R4.11在固定产品提交 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d` 上完成受支持安装和唯一一次正式请求。安装件合同3项通过；请求返回HTTP 200、运行退出码0、`termination_reason=completed`，包含4个正式子线程。第一轮记录失败并只触发一次修正，第二轮记录 `pass_with_minor` 并停止；两轮固定写入、保存、摘要绑定和完成报告符合合同；终态后只重建一次总览。流程结果通过，内容结果为 `pass_with_minor`。

R4.11第一轮的三个阻断问题都归属 `direction:DIR00001`；记录后交给修正入口的校验文件没有被替换，也没有文件级问题。`47c58de` 对该输入仍从正式状态读取同一个方向、问题和候选编号，不改变根对话的派发次数、固定写入、保存、记录、第二轮停止或终态重建。C组当前两项确定性检查负责证明新增的文件级展开行为和改写文件限制；R4.11继续证明真实Codex路径及调用顺序。两者没有重复证明同一目标，因此R4.11的E组结果继续适用，不安装新消费者、不发送模型请求，也不创建事件判定程序。

## 当前唯一执行步骤

本地测试工程师先按C组当前修正要求补齐现有两项测试；修订后的测试源码和本计划通过第二关后，才可正式执行。执行前记录计划版本、当前测试提交和产品修改提交，并确认 `contact_state.py` 相对 `47c58de` 没有变化；不一致时停止。只执行下面两个受影响方法：

```sh
set -eu
set -o pipefail
run_dir=$(mktemp -d /private/tmp/issue66-pr73-r416.XXXXXX)
printf '%s\n' 'issue-66-test-plan-new-rules-r4.16-2026-10-10' > "$run_dir/plan-version.txt"
git rev-parse HEAD > "$run_dir/tested-sha.txt"
git rev-parse 47c58de235f8e18db1e8a2520c9fa80c6d145b0f > "$run_dir/product-sha.txt"
git diff --exit-code 47c58de235f8e18db1e8a2520c9fa80c6d145b0f -- \
  .apm/skills/professor-contact/scripts/contact_state.py \
  > "$run_dir/product-diff.log"
cd .apm/skills/professor-contact/tests
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -m unittest -v \
  test_contact_state.Issue66RecordedValidationScopeTests.test_handoff_record_expands_global_blocker_to_rendered_objects \
  test_contact_state.Issue66RecordedValidationScopeTests.test_rewritten_validation_file_cannot_expand_or_replace_recorded_correction \
  2>&1 | tee "$run_dir/affected-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/affected-tests.exit"
test "$test_exit" -eq 0
```

通过条件为产品文件与 `47c58de` 一致、精确收集并运行2项、两项均通过、退出码0。命令启动失败、测试无法收集或版本证据缺失记为未执行或证据不足；断言正常运行后失败才记对应业务检查失败。不得扩大到完整42项，不得重复运行B、D组检查，不得发送E组请求。

## 当前状态

- A：R4.12结果继续适用。
- B、D：R4.15两项结果继续适用，输出为 `Ran 2 tests in 2.894s`、`OK`、退出码0，记录目录为 `/private/tmp/issue66-pr73-r415.TF3qu0`；`47c58de` 没有修改这两个目标或测试方法。
- C：R4.12未受影响结果继续适用；当前两项测试仍须按本计划补齐，已有持续集成通过只作历史记录，不代替修订后的正式结果。
- E：按本节影响判断继续采用R4.11流程结果，内容结果为 `pass_with_minor`，不追加模型请求。
- 第二关须审核R4.16设计、两项测试修订和执行步骤；通过后由本地测试工程师运行当前两项。第三关再审核测试提交、输出、退出码及结果适用性。本计划不自行批准第二关、第三关或合并。
