# 边界四：证据快照与决策阶梯搬移（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-18 授权“Stage4/5 证据处理”的后半（快照与决策阶梯）；原文见执行计划。
- 对照基准：`cdd01f7f2c03be822adbb5a4117c7e65a89d6c82`。
- Target repository revision: 工作分支 `refactor-evidence-ladder` 实施后的提交。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`；提交前按共用清单 `plan/test-plan-checklist.md` 自检（该清单随 PR #98 引入，本分支不把它当作已存在的文件；自检小节已逐条写明）。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | `contact_evidence_snapshot` 的内容、sha 绑定与三位置签名不变 | 同一驱动分别加载基准与改动版：五种 artifact（正常记录、冲突记录、`paper_only`、降级 artifact、查不到的教授）与一次“无 artifact + 错误码”；另比较 runner 侧签名 | 六种情况的返回字典逐字段相同；runner 侧签名逐字相同（三位置参数） | 仓库外驱动 `ladder_probe.py`，两侧放**同构目录**后逐字段 `diff` |
| T2 | 决策阶梯的判定与字段不变 | 共 32 组：① 24 组状态矩阵（4 种 `state`：fresh／stale／unavailable／None × 3 种 `checker_error`：None／script_missing／script_failed × 2 种 `rebuild_ran`）；② 2 种 `artifact_error`（不可读／缺失）；③ 1 组 **artifact 级** `degraded` 标志（结果为 accept；逐记录降级升级由 T5 覆盖）；④ **5 条 verdict 分支**：`insufficient` → `contact_evidence_insufficient`、`confirmed_cross_source` 且 `current_email=None` → `contact_evidence_ambiguous`、verdict 不在 `CONTACT_EVIDENCE_VERDICTS`（`bogus`）→ `contact_evidence_invalid_record`、`paper_only` → `contact_evidence_paper_only`、`conflict` → `contact_evidence_conflict` | 每组返回的完整决策对象（`status`／`reason_code`／`web_lookup_required`／`recipient_email`／`sources` 等）逐字段相同 | 同 T1 |
| T3 | `contact_evidence_decisions` 的逐教授路由与返回键不变 | 三条 email（同一教授重复一次 + 一个无证据的教授）与一份 `resolved` 字典 | 决策字典的键集合与每个值逐字段相同（同一教授只出现一次） | 同 T1 |
| T4 | `contact_evidence_freshness_reason` 的 30 天边界不变 | 8 种输入：当天、29 天前、30 天前、31 天前、未来时间、`None`、非时间字符串、数字 | 返回值（`None` 或原因串）逐项相同 | 同 T1 |
| T5 | 既有证据入口不受影响 | 阶梯判定与快照的既有用例 | 全部通过 | `test_contact_evidence_ladder`（整模块 40 项：该文件每个用例都以阶梯判定或快照为主要目的）与 `test_stage5_fixture_isolation`（模块 2 项：显式注入的 checker 与快照隔离），共 42 项 |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的全量 `unittest discover` 由仓库工作流照常执行，其结果单独引用，不作为本批业务必测项；合并要求继续按仓库规则执行。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-evidence-ladder` 内进行；脚本与运行产物放仓库外 `/tmp`（复跑时用 `mktemp -d /tmp/pc-bnd4-XXXXXX` 新建；本批执行记录沿用 `/tmp/pc-bnd4-check/` 并已点名）。

1. 准备：确认工作树只有本批改动、Python 可用，把**两侧**都复制成同构目录（各自带全部 `_*.py` 兄弟模块），并把驱动脚本复制进本轮目录。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-evidence-ladder
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-bnd4-XXXXXX)
   mkdir -p "$RUN/base" "$RUN/head"
   for name in contact_state _stage3_render _contact_io _stage3_handoff _contact_evidence; do
     git show cdd01f7f2c03be822adbb5a4117c7e65a89d6c82:.apm/skills/professor-contact/scripts/$name.py > "$RUN/base/$name.py"
   done
   cp .apm/skills/professor-contact/scripts/contact_state.py .apm/skills/professor-contact/scripts/_*.py "$RUN/head/"
   cp /tmp/pc-bnd4-check/ladder_probe.py "$RUN/ladder_probe.py"
   ```
   两侧必须放在同构目录：runner 在导入期按 `Path(__file__).with_name(...)` 加载兄弟模块，只有文件名正确、且两侧各自成套时才可比。驱动来源缺失时按执行记录点名的目录找回同一脚本，仍找不到就停止并交计划所有人，不得凭提纲重写比较方法。
2. T1–T4：以两侧的 runner 为参数各跑一次驱动，再比较。
   ```sh
   set -e
   uv run --no-project "$RUN/ladder_probe.py" "$RUN/base/contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/ladder_probe.py" "$RUN/head/contact_state.py" "$RUN/head-work" > "$RUN/head.json"
   jq 'del(.injection_sites)' "$RUN/base.json" > "$RUN/base.filtered.json"
   jq 'del(.injection_sites)' "$RUN/head.json" > "$RUN/head.filtered.json"
   diff -u "$RUN/base.filtered.json" "$RUN/head.filtered.json" && echo "T1-T4 IDENTICAL"
   ```
   预期：两条驱动命令都退出 0（否则 `set -e` 立即中止），`diff` 无输出并打印 `T1-T4 IDENTICAL`。过滤后的中间文件用 `jq` 生成、不依赖进程替换，POSIX shell 下同样可执行。**`injection_sites` 是唯一被排除的键**：它是本批已批准的签名变化（三个别名新增关键字参数，见执行计划“unresolved impact”），两侧各自单独核对：
   ```sh
   set -e
   jq -c '.injection_sites' "$RUN/base.json"
   jq -c '.injection_sites' "$RUN/head.json"
   ```
   预期：基准侧 8 个名字全部为空数组；改动侧 `contact_evidence_record` 为 `["compact_name"]`、`contact_evidence_freshness_reason` 为 `["verify_ttl_days"]`、`_evaluate_record_ladder` 为三者，其余五个（含三个包装）为空数组。
3. T5：只跑清单列出的两个入口。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-evidence-ladder/.apm/skills/professor-contact/tests
   python3 -m unittest test_contact_evidence_ladder test_stage5_fixture_isolation -v
   ```
   预期：`Ran 42 tests`、全部 `ok`（40 + 2）。`test_contact_evidence_ladder` 整模块纳入的理由：该文件只有一个类，40 个用例全部以阶梯判定、快照或 checker 交互为主要目的；其它 Stage5 用例（选择、渲染、事务）不属本批，不作为通过条件。
4. 记录：保存命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并写入 `test-execution-<日期>.md`；既有仓库检查按运行编号与所跑 head 单独记录。
5. 失败处理：出现差异按函数定位，判定为产品缺陷交实现负责人修正后重跑受影响编号；既有用例失败区分“本次引入／既有失败／环境问题”；既有跳过项按未执行记录。

## 驱动脚本要点（T1–T4）

- 用 `importlib.util.spec_from_file_location` 按路径加载传入的 runner。
- **签名适配**：基准修订里 `contact_evidence_record`／`contact_evidence_snapshot`／`contact_evidence_freshness_reason`／`_evaluate_record_ladder`／`evaluate_contact_evidence`／`contact_evidence_decisions` 不需要注入参数，改动修订的模块版需要；驱动用 `inspect.signature` 判断后按需传 `compact_name`／`sha256_obj`／`verify_ttl_days`，两侧同一逻辑，且不吞异常。
- artifact 使用**固定时间戳**（不取当前时间），否则两侧文档里的 `generated_at` 会因运行时刻不同而产生假差异；T4 的输入才按“当前时间减 N 天”构造，其结果（`None` 或原因串）与时间无关。
- 输出在打印前把工作目录替换为 `<WORK>`。

## 环境与预检

- 使用仓库现有的本地 Python（记录 `python3 --version` 实际值）与既有夹具；驱动只用标准库与 `jq`（用于按键过滤 JSON）。
- 测试只使用合成数据与临时目录；不接触用户业务资料。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 上游定位/检查/重建（`upstream_check_script` 等） | 已在边界三完成并取得三关口通过 |
| Stage4/5 的选择、渲染与事务路径 | 不属本批搬移范围 |
| 全仓本地回归 | 作为既有仓库检查单独引用 CI 结果 |

## 自检

按 `plan/test-plan-checklist.md` 逐条核对：① 必测项只引用能证明本批行为的方法（T5 的两个入口）；② CI 不在必测清单；③ 驱动脚本有确切来源与 `cp` 命令，两侧同构目录；④ 命令块全部 `set -e`；⑤ 差异走“同构目录对照 + 逐字段比较”，唯一排除键（`injection_sites`）是本批已批准的签名变化并单独核对；⑥ 计划与执行记录使用同一套标签；⑦ 编号为 T1–T5、版本指针与执行计划第 2 版一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一关口的 B1 补上三条此前零覆盖的阶梯分支（`insufficient`／`ambiguous`／`invalid_record`，另加 `paper_only` 与 `conflict` 共 5 条 verdict 分支），矩阵计数由“21 组”更正为 32 组，说明“降级”案例实际打的是 artifact 级标志（逐记录降级由 T5 覆盖），并把过滤步骤改成写临时文件（不依赖进程替换），基准侧的 `injection_sites` 也改为显式断言全空。

## 审核状态

测试计划第 2 版为当前唯一版本。第 1 版第二关口 PASS、第一关口有 1 项 blocker（B1），已按上节修正。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
