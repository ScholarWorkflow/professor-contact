# 边界三：联系证据上游定位、检查与重建搬移（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版。
- 需求来源：负责人 2026-10-18 授权的“其余边界”中“Stage4/5 证据处理”的上游定位/检查/重建部分；原文见执行计划。
- 对照基准：`2117fc6a1607a22aa9e723002b4a78625733b7b1`。
- Target repository revision: 工作分支 `refactor-contact-evidence` 实施后的提交。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`，提交前按 `plan/test-plan-checklist.md` 自检（该文件随 PR #98 引入；本计划的自检小节已逐条写明，不依赖它已在本分支存在）。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | `upstream_check_script` 的三级解析与失败关闭不变 | 同一驱动分别加载基准与改动后的 runner：显式注入指向存在的文件、指向不存在的文件、注入空白串、不注入（无 sibling/兄弟 checkout 的等价目录布局） | 四种情况下返回的路径或 `None` 逐项相同；注入空白串与不注入都退回环境解析 | 仓库外驱动脚本（`evidence_probe.py`）在**同构目录**里跑两侧后逐字段 `diff`；安装布局解析另由 T5 的既有用例覆盖 |
| T2 | `resolve_contact_evidence` 的检查/重建顺序、失败返回与返回值不变 | 用仓库外的 stub `contact_evidence.py`（每次调用把 `check`/`rebuild` 写进日志）制造八种场景：fresh；stale（重建成功）；**per-professor unavailable**；无 per-professor 条目的顶层 unavailable；重建失败（非零退出）；check 非零退出；check 输出非 JSON；check 的 `result` 非法值。每次都调用 `resolve_contact_evidence(program_root, ["試験 教授"])` | 八种场景返回字典的 5 个键与内容相同；调用日志序列相同：fresh → `check`；stale → `check, rebuild, check`；per-professor unavailable → `check`（**不重建**）；无条目 unavailable → `check, rebuild, check`；重建失败 → `check, rebuild` 且 `rebuild_ran: False`；三种 check 失败 → `check` 且 `checker_error: script_failed`、不重建 | 同 T1；stub 与日志放在各自工作目录，输出归一化后比较 |
| T3 | `load_contact_evidence` 的校验与单参数可用性不变 | 合法 artifact、kind 不符、schema 不符、非对象、坏 JSON、文件缺失六种输入；并检查 runner 侧 `load_contact_evidence` 的签名 | 六种输入返回的 `(artifact, error)` 逐项相同；runner 侧签名仍是 `(program_root)` 单参数 | 同 T1；签名用 `inspect.signature` 比较 |
| T4 | `professor_source_state` 与 `source_state_needs_rebuild` 不变 | 六种教授名形态（全角空格、首尾空格、stale/legacy/invalid/不存在）；七种状态（None/fresh/stale/legacy/invalid/unavailable/空对象）；并检查 runner 侧 `professor_source_state` 的两个位置参数签名 | 归一化匹配结果与 `source_state_needs_rebuild` 判定逐项相同；runner 侧签名仍是 `(report, professor)` | 同 T1；测试里已有的两位置参数直调由 T5 覆盖 |
| T5 | 既有上游证据入口不受影响（只选以本批行为为主要目的的入口） | 安装布局解析、wrapper finalize 的 checker 定位、显式注入隔离、真实脚本 argv 路径 | 全部通过 | `test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling`、`test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_fixture_isolation`（模块 2 项，均以显式注入与隔离为主要目的）、`test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_3_unrelated_stale_source_state_cannot_rebuild_for_a` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的全量 `unittest discover` 由仓库工作流照常执行，其结果单独引用，不作为本批业务必测项；合并要求继续按仓库规则执行。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-contact-evidence` 内进行；脚本与运行产物放仓库外 `/tmp`（本次用 `mktemp -d /tmp/pc-bnd3-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，把**两侧**都复制成同构目录，并把驱动脚本复制进本轮目录。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-contact-evidence
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-bnd3-XXXXXX)
   mkdir -p "$RUN/base" "$RUN/head"
   for name in contact_state _stage3_render _contact_io _stage3_handoff; do
     git show 2117fc6a1607a22aa9e723002b4a78625733b7b1:.apm/skills/professor-contact/scripts/$name.py > "$RUN/base/$name.py"
   done
   cp .apm/skills/professor-contact/scripts/contact_state.py .apm/skills/professor-contact/scripts/_*.py "$RUN/head/"
   cp /tmp/pc-bnd3-check/evidence_probe.py "$RUN/evidence_probe.py"
   ```
   **两侧必须放在同构目录**：`upstream_check_script` 用 `Path(__file__).resolve().parents` 解析同级 skill 与兄弟 checkout，基准副本留在 `/tmp`、改动版留在仓库目录会让两侧解析结果天然不同（会产生假差异）。驱动来源缺失时按执行记录里的运行目录找回同一脚本，仍找不到就停止并交计划所有人，不得凭提纲重写。
2. T1–T4：以两侧的 runner 为参数各跑一次驱动，再比较。
   ```sh
   set -e
   uv run --no-project "$RUN/evidence_probe.py" "$RUN/base/contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/evidence_probe.py" "$RUN/head/contact_state.py" "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T4 IDENTICAL"
   ```
   预期：两条驱动命令都退出 0（否则 `set -e` 立即中止），`diff` 无输出并打印 `T1-T4 IDENTICAL`。驱动在打印前把工作目录替换为 `<WORK>`，避免绝对路径造成假差异。
3. T5：只跑清单列出的入口。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-contact-evidence/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_fixture_isolation \
     test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_3_unrelated_stale_source_state_cannot_rebuild_for_a \
     -v
   ```
   预期：`Ran 5 tests`、全部 `ok`（2 + 1 + 1 + 1；`test_stage5_fixture_isolation` 模块本身只有 2 个用例，且都以上游 checker 的显式注入与隔离为主要目的）。其它 Stage5 证据用例（阶梯/快照/决策）属下一批范围，不作为本批通过条件。
4. 记录：保存命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并写入 `test-execution-<日期>.md`；既有仓库检查按运行编号与所跑 head 单独记录。
5. 失败处理：出现差异按函数定位，判定为产品缺陷交实现负责人修正后重跑受影响编号；既有用例失败区分“本次引入／既有失败／环境问题”；既有跳过项按未执行记录。

## 驱动脚本要点（T1–T4）

- 用 `importlib.util.spec_from_file_location` 按路径加载传入的 runner，模块名带唯一后缀。
- **签名适配**：基准修订里 `load_contact_evidence`／`professor_source_state`／`resolve_contact_evidence` 不需要注入参数，改动修订的模块版需要；驱动用 `inspect.signature` 判断后按需传 `read_json_file`／`compact_name`，两侧同一逻辑，且不吞异常。
- T1 的四种注入场景用 `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 控制，结束后恢复原值。
- T2 的 stub 脚本按 `STUB_MODE` 输出报告并把 `check`/`rebuild` 追加到 `STUB_LOG`（每个场景开始前清空）：`fresh`／`stale`／`unavailable_record`（带 per-professor 条目）／`empty_report`（无条目）／`rebuild_fails`（重建非零退出）／`exit_nonzero`／`bad_json`／`bad_result`。**per-professor unavailable 必须带条目**，否则 `professor_source_state` 返回 None 会触发重建，验证的就不再是“unavailable 不重建”这条分支。
- T3/T4 的输入构造与 runner 侧签名（`load_contact_evidence(program_root)`、`professor_source_state(report, professor)`）一并比较，用来钉住“三个同签名包装”这一契约。

## 环境与预检

- 使用仓库现有的本地 Python（记录 `python3 --version` 实际值）与既有夹具；驱动只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料；`PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 在每个场景后恢复。
- 预检只确认命令可用、工作树状态、两侧副本可生成；不预先执行业务目标命令求结果。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 证据快照与决策阶梯（`contact_evidence_snapshot`、`evaluate_contact_evidence`、`contact_evidence_decisions` 等） | 属下一批（执行计划“非目标”） |
| 上游 `contact_evidence.py` 自身行为 | 不在本仓，本批只动调用侧 |
| 全仓本地回归 | 作为既有仓库检查单独引用 CI 结果 |

## 自检

按 `plan/test-plan-checklist.md` 逐条核对：必测项只引用能证明本批行为的方法（T5 的 5 个入口）；CI 不在必测清单；驱动脚本有确切来源与 `cp` 命令；命令块全部 `set -e`；失败/差异走“同构目录对照 + 逐字段比较”，注入场景覆盖 fresh/stale/unavailable 与四种解析路径；计划与执行记录使用同一套标签；编号为 T1–T5、版本指针与执行计划第 3 版一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一关口的两个 blocker 修正——B1 在 T2 里补 check 的三种失败返回（非零退出／非 JSON／`result` 非法值）与重建失败（`False`）场景，覆盖契约里明写的 `script_failed`／`False`；B2 把 `unavailable` 场景改成带 per-professor 条目的报告（此时日志为 `check`，不再重建），并另加“无条目报告”场景写明它仍会重建一次。

## 审核状态

测试计划第 2 版为当前唯一版本。第 1 版第二关口 PASS、第一关口有两项 blocker，已按上节修正。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
