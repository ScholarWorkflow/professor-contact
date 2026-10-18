# 边界二：Stage 3 校验交接原语移入内部模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版。
- 需求来源：负责人 2026-10-18 授权的“其余边界”中“Stage3 提交与校验交接”的校验交接部分；原文见执行计划。
- 对照基准：`779fb692ed5ded163ab0eb5b415aef698135f54e`。
- Target repository revision: 工作分支 `refactor/stage3-handoff` 实施后的提交。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 缓冲式持久写入与失败清理不变 | 同一驱动分别加载基准与改动后的 runner：小块写入、76800 B（跨多个 64 KiB 回读分块）写入、对已存在路径写入（`O_EXCL` 失败）；再直接验证 `_stage3_created_file_identity` 与 `_stage3_cleanup_incomplete_write`（身份一致／不一致／None）三个分支 | 成功时文件字节、权限模式（`st_mode & 0o777`）、无残留临时文件；已存在路径写入抛 `FileExistsError` 且原文件不变；身份一致时删除、不一致或 None 时保留 | 仓库外驱动脚本，两侧输出规范化 JSON 后 `diff`；集成侧“写入期失败后清理、只删本次文件、抛 `OSError`”由 T5 的批量写/回读失败用例端到端覆盖 |
| T2 | 严格 JSON 对象解析不变 | 合法对象、重复键对象、含 `NaN`/`Infinity` 的文本、数组、坏 UTF-8 字节 | 合法输入解析结果相同；重复键与 `NaN`/`Infinity` 抛 `ValueError`；数组两侧同样返回列表（“必须是非对象”的拒绝发生在下游归一化，由 T5 的真实写校验路径覆盖）；坏字节抛相同异常 | 同 T1 |
| T3 | invocation 参数映射不变 | 给定 invocation 字典与调用参数：含来源参数、含被忽略参数、缺来源字段 | 返回对象的字段名与取值逐项相同；只覆盖 invocation 记录的来源参数 | 同 T1 |
| T4 | 作用域解析、路径归一化与轮次守卫不变 | ① `stage3_render_line_scopes` 对五份代表性渲染文本（direction/group 标记、标题后四行内/外、无标记、**同一标记重复出现**）；② `_stage3_normalized_absolute_path` 对合法、相对、空、非字符串四类输入；③ `_require_stage3_handoff_round` 对 7 组状态（round 1 未记录/已记录、round 2 无前轮/耗尽/有待修正/渲染变化/正常） | ① 五份文档返回的作用域列表逐项相同（内容与顺序）；② 非法路径给出相同的错误 JSON 与退出码，合法路径返回相同的绝对路径字符串；③ 6 个失败原因码与正常路径判定全部相同 | 同 T1；失败调用捕获 `SystemExit` 与 stdout。`_stage3_validation_files`／`_stage3_complete_write_result`／`_stage3_issue_scopes` 的归一化不在驱动里单独构造，由 T5 的真实交接流程覆盖 |
| T5 | 既有 Stage 3 校验交接路径不受影响 | 真实 CLI 流程：`stage3-prepare-validation` → 写入校验结果 → `stage3-save-validation` → `stage3-record-validation`；以及 scope 归属、修正轮与批量写入失败清理 | 全部通过 | 引用既有用例：`test_stage3_validation_refine`（18）、`test_issue66_validation_handoff`（12）、`test_stage3_direction_groups`（19）、`test_issue66_stage3_local_state`（6）。前三个共 49 项直接落在被移动原语及其路径上；第四个 6 项属相邻的本地提交/回滚面（本批非目标），因共用夹具且覆盖 record 路径写入的状态而保留，可按验收决定人要求裁掉 |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的全量 `unittest discover` 由仓库工作流照常执行，其结果单独引用，不作为本批业务必测项，也不因本批而扩张或缩减；合并要求继续按仓库规则执行。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff` 内进行；驱动脚本与运行产物放仓库外 `/tmp`（本次用 `mktemp -d /tmp/pc-bnd2-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，取出基准修订的 runner **及其依赖的兄弟模块**，并把上一轮实际使用的驱动脚本复制进本轮目录。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-bnd2-XXXXXX)
   for name in contact_state _stage3_render _contact_io; do
     git show 779fb692ed5ded163ab0eb5b415aef698135f54e:.apm/skills/professor-contact/scripts/$name.py > "$RUN/base_$name.py"
   done
   mv "$RUN/base_contact_state.py" "$RUN/contact_state.py"
   mv "$RUN/base__stage3_render.py" "$RUN/_stage3_render.py"
   mv "$RUN/base__contact_io.py" "$RUN/_contact_io.py"
   cp /tmp/pc-bnd2-check/handoff_probe.py "$RUN/handoff_probe.py"
   ```
   基准修订已含批次二/三与边界一，runner 在导入期按 `Path(__file__).with_name(...)` 加载 `_stage3_render.py` 与 `_contact_io.py`，因此三个文件必须放在同一目录。最后一条是必须的：驱动自带输入构造与断言；来源缺失时按执行记录里记录的该轮目录找回同一脚本，仍找不到就停止并交计划所有人，不得凭提纲重写比较方法。
2. T1–T4：同一驱动脚本分别以基准目录副本与工作树 runner 为参数运行，各产出一份规范化 JSON，再比较。`set -e` 保证任一侧运行失败立即中止，不会出现“两侧都失败、输出都为空、`diff` 仍然成功”的假结论。
   ```sh
   set -e
   uv run --no-project "$RUN/handoff_probe.py" "$RUN/contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/handoff_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T4 IDENTICAL"
   ```
   预期：两条驱动命令都退出 0（否则 `set -e` 立即中止），`diff` 无输出并打印 `T1-T4 IDENTICAL`。
3. T5：既有 Stage 3 校验交接用例。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff/.apm/skills/professor-contact/tests
   python3 -m unittest test_stage3_validation_refine test_issue66_validation_handoff \
     test_issue66_stage3_local_state test_stage3_direction_groups -v
   ```
   预期：全部 `ok`，无 `FAIL`/`ERROR`。
4. 既有仓库检查：推送到 PR 后引用仓库 CI 的全量结果（不属于本批必测项）；CI 未通过时按第 6 步处理。
5. 记录：保存命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并写入 `test-execution-<日期>.md`。
6. 失败处理：出现差异按函数定位，判定为产品缺陷交实现负责人修正后重跑受影响编号；既有用例失败区分“本次引入／既有失败／环境问题”；既有跳过项按未执行记录。

## 驱动脚本要点（T1–T4）

- 用 `importlib.util.spec_from_file_location` 按路径加载传入的 runner，模块名带唯一后缀。
- **签名适配**：基准修订里这六个函数不需要 `fail`，改动修订把它们改成关键字参数。驱动用一个适配函数判断签名（`inspect.signature` 是否含 `fail` 参数），需要时传 `fail=runner.fail`，并对两侧使用同一适配逻辑；这份适配只存在于仓库外驱动里，不进产品。
- 失败调用：用 `contextlib.redirect_stdout` 捕获输出、`try/except SystemExit` 记录退出码；业务通道内的失败用 `with runner.professor_business_channel()` 包裹并捕获 `runner.ProfessorBusinessFailure`。
- 输出只含相对路径、文件内容、权限模式（`stat` 的 `st_mode & 0o777`）、异常类型名与错误 JSON 文本，便于两侧直接 `diff`。
- T1 的身份/清理验证采用执行版写法：直接调用 `_stage3_created_file_identity` 与 `_stage3_cleanup_incomplete_write` 覆盖“身份一致删除／不一致保留／None 保留”三个分支（比“写入中途替换身份”的注入更清晰且不依赖时序）；集成侧的失败清理由 T5 的批量写/回读失败用例承担。
- 输出规范化：两侧各自使用独立工作目录，脚本在打印前把工作目录前缀替换为 `<WORK>`，避免绝对路径与异常消息里的目录名造成假差异。
- T4 的作用域输入要覆盖：标题后四行内的 `<!-- stage3_scope: {...} -->`、四行外（应被忽略）、`<!-- candidate_meta: ... -->`、重复标记、非 JSON 标记（应触发失败）。

## 环境与预检

- 使用仓库现有的本地 Python（记录 `python3 --version` 实际值）与既有夹具；驱动只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、基准 runner 与两个兄弟模块能取出；不预先执行业务目标命令求结果。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块的独立单元测试 | 属内部组织；T1–T4 已用基准修订对照直接验证行为 |
| 凭证与交接文件层、四个 CLI 处理器、受管文档写入 | 本批不动这些函数（执行计划“非目标”已说明） |
| Stage4/5 证据处理 | 另立 PR |
| 全仓本地回归 | 仓库 CI 已在 PR 上执行全量 discover，按 `Test Engineer Rule.md` 第 6 节直接引用 |

## 自检

提交审核前逐条核对（与仓库 `plan/test-plan-checklist.md` 同一口径）：必测项只引用能证明本批行为的方法；CI 不在必测清单；每个临时脚本都有确切来源与复制命令；命令块启用 `set -e`；失败注入到达目标分支；计划文字与执行记录用同一套标签。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 3 版：按与批次三/边界一相同的口径整理——仓库 CI 从业务必测清单移出（T6 撤销，改为“既有仓库检查”单独引用）；第 1、2、3 步的命令块启用 `set -e` 并写明“两条驱动命令都须退出 0 才比较”；第 1 步补 `cp` 复制驱动脚本的明确命令与缺失时的处理；新增“自检”小节。必测编号由 T1–T6 收为 T1–T5。
- 第 2 版：按第一、二关口的非阻断意见修正——T1 的注入描述改成执行版的三分支清理验证；T2 更正“非对象抛 `ValueError`”的说法（数组正常解析，非对象拒绝在下游归一化、由 T5 覆盖）；T4 标题改为“作用域解析、路径归一化与轮次守卫”并注明归一化由 T5 覆盖，驱动补“同一标记重复出现”用例；执行计划版本指针更新为第 3 版。T5 的四个模块保留（前三个共 49 项直接落在被移动原语上，第四个 6 项属相邻面、可按验收决定人要求裁掉）。

## 审核状态

测试计划第 3 版为当前唯一版本；第 1 版已取得第一、二关口 PASS（无 blocker），第 2 版只落实该轮的非阻断意见；第 3 版按统一自检口径把 CI 移出必测清单、补齐脚本复制步骤并启用 `set -e`（T6 撤销，编号收为 T1–T5）。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
