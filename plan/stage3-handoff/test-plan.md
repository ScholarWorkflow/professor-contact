# 边界二：Stage 3 校验交接原语移入内部模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版。
- 需求来源：负责人 2026-10-18 授权的“其余边界”中“Stage3 提交与校验交接”的校验交接部分；原文见执行计划。
- 对照基准：`779fb692ed5ded163ab0eb5b415aef698135f54e`。
- Target repository revision: 工作分支 `refactor/stage3-handoff` 实施后的提交。
- Test plan revision: 第 1 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 缓冲式持久写入与失败清理不变 | 同一驱动分别加载基准与改动后的 runner：写入一段含非 ASCII 的字节；再用“写入中途目标身份被替换”制造失败 | 成功时文件字节、权限模式、无残留临时文件；失败时按身份删除本次写入的文件、抛出 `OSError`、不误删他人文件 | 仓库外驱动脚本，两侧输出规范化 JSON 后 `diff` |
| T2 | 严格 JSON 对象解析不变 | 合法对象、重复键对象、含 `NaN`/`Infinity` 的文本、数组、坏 UTF-8 字节 | 合法输入解析结果相同；`NaN`/`Infinity` 抛 `ValueError`；非对象输入抛 `ValueError`；坏字节抛 `UnicodeDecodeError`／`ValueError` | 同 T1 |
| T3 | invocation 参数映射不变 | 给定 invocation 字典与调用参数：含来源参数、含被忽略参数、缺来源字段 | 返回对象的字段名与取值逐项相同；只覆盖 invocation 记录的来源参数 | 同 T1 |
| T4 | 校验结果归一化与作用域解析不变 | ① `stage3_render_line_scopes` 对同一份代表性渲染文本（含 direction/group 标记、标题后四行内/外的标记、重复标记）；② `_stage3_normalized_absolute_path` 对合法与非法路径；③ `_require_stage3_handoff_round` 对轮次 1／2／超限 | ① 返回的作用域列表逐项相同（内容与顺序）；② 非法路径给出相同的错误 JSON 与退出码，合法路径返回相同的绝对路径字符串；③ 轮次判定与失败原因码相同 | 同 T1；失败调用捕获 `SystemExit` 与 stdout |
| T5 | 既有 Stage 3 校验交接路径不受影响 | 真实 CLI 流程：`stage3-prepare-validation` → 写入校验结果 → `stage3-save-validation` → `stage3-record-validation`；以及 scope 归属与修正轮 | 全部通过 | 引用既有用例：`test_stage3_validation_refine`、`test_issue66_validation_handoff`、`test_issue66_stage3_local_state`、`test_stage3_direction_groups` |
| T6 | 未改动区域的既有门禁 | 仓库 CI 对 PR 提交跑全量 `unittest discover` | 全量通过 | 直接引用 PR 的 CI 结果 |

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-handoff` 内进行；驱动脚本与运行产物放仓库外 `/tmp`（本次用 `mktemp -d /tmp/pc-bnd2-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，并取出基准修订的 runner **及其依赖的兄弟模块**。
   ```sh
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
   ```
   基准修订已含批次二/三与边界一，runner 在导入期按 `Path(__file__).with_name(...)` 加载 `_stage3_render.py` 与 `_contact_io.py`，因此三个文件必须放在同一目录。
2. T1–T4：同一驱动脚本分别以基准目录副本与工作树 runner 为参数运行，各产出一份规范化 JSON，再比较。
   ```sh
   uv run --no-project "$RUN/handoff_probe.py" "$RUN/contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/handoff_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T4 IDENTICAL"
   ```
   预期：`diff` 无输出并打印 `T1-T4 IDENTICAL`。
3. T5：既有 Stage 3 校验交接用例。
   ```sh
   cd .apm/skills/professor-contact/tests
   python3 -m unittest test_stage3_validation_refine test_issue66_validation_handoff \
     test_issue66_stage3_local_state test_stage3_direction_groups -v
   ```
   预期：全部 `ok`，无 `FAIL`/`ERROR`。
4. T6：推送到 PR 后引用仓库 CI 的全量结果；CI 未通过时按第 6 步处理。
5. 记录：保存命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并写入 `test-execution-<日期>.md`。
6. 失败处理：出现差异按函数定位，判定为产品缺陷交实现负责人修正后重跑受影响编号；既有用例失败区分“本次引入／既有失败／环境问题”；既有跳过项按未执行记录。

## 驱动脚本要点（T1–T4）

- 用 `importlib.util.spec_from_file_location` 按路径加载传入的 runner，模块名带唯一后缀。
- **签名适配**：基准修订里这六个函数不需要 `fail`，改动修订把它们改成关键字参数。驱动用一个适配函数判断签名（`inspect.signature` 是否含 `fail` 参数），需要时传 `fail=runner.fail`，并对两侧使用同一适配逻辑；这份适配只存在于仓库外驱动里，不进产品。
- 失败调用：用 `contextlib.redirect_stdout` 捕获输出、`try/except SystemExit` 记录退出码；业务通道内的失败用 `with runner.professor_business_channel()` 包裹并捕获 `runner.ProfessorBusinessFailure`。
- 输出只含相对路径、文件内容、权限模式（`stat` 的 `st_mode & 0o777`）、异常类型名与错误 JSON 文本，便于两侧直接 `diff`。
- T1 的“中途身份被替换”注入：写入过程中把目标路径替换为另一个文件（或在写入函数内部记录目标身份后替换），用于验证“只删除本次写入且身份未变的文件”；若该注入在基准与改动侧都不可行，退化为“写入失败后无残留 + 原文件不变”，并在记录里注明。
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

## 修订记录

- 第 1 版：首次提交测试计划审核。

## 审核状态

测试计划第 1 版为当前唯一版本，状态为待审核。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
