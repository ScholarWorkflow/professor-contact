# Stage 3 划分第二批：plan／finalize／overview 命令（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#118）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage3-commands`，父提交为堆栈末位 `refactor-stage3-validation`（#118）的 head `e303a1c`。基准一律用 `git rev-parse origin/refactor-stage3-validation` 动态取。
- 参考做法：`_stage3_validation.py`、`_stage3_render.py`、`_stage3_handoff.py`、`_contact_*`、`_stage2_*` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 4 个 Stage 3 命令与作用域 helper 离开 runner 顶层 | 4 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage3_commands.py` 的 `build()` 内；runner 有 4 个同名别名 |
| R2 | 搬移不改变逻辑 | 4 个定义体除缩进外逐字相同；自由名字全部来自 `build()` 的 56 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage3_commands.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `canonical_professor_dir` 结束之后（它是 56 个注入名里最晚定义的一个，2624 行）；四个别名都在 `main()` 运行前建立 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、四段定义删除；删除后合并出的两处空行块（4 行、7 行）收敛为 2；父提交自带的 6 行块（产物中约 3939–3944）保持原尺寸，**绑定块两侧固定 2 行**（产物里 1771–1773 的 3 行块就是绑定块插入形成的，不是父提交自带） |

## 范围：4 个定义、924 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `_stage3_selected_scope_keys` | 981–1034 | 54 |
| `cmd_stage3_plan` | 1108–1498 | 391 |
| `cmd_stage3_finalize` | 1808–2194 | 387 |
| `cmd_stage3_rebuild_overview` | 2197–2288 | 92 |

合计 924 行，落在四段（981–1034、1108–1498、1808–2194、2197–2288），段间保留 `_stage3_validation` 的绑定块（1049–1086）与其它定义。

### 需要注入的 56 个名字

- Stage 2 与共享层产出的别名（约 40 个）：`atomic_write@56`、`staged_pair_commit@59`、`emit@60`、`fail@65`、`soft_exit@66`、`MANAGED_BY@298`、`CANDIDATE_STATE_SCHEMA@306`、`DIRECTION_IDENTITY_VERSION@314`、`STAGE3_GENERATOR_CONTRACT_VERSION@315`、`CANDIDATE_STATE_KIND@318`、`INPUT_PACK@330`、`CANDIDATE_STATE@331`、`CANDIDATES_MD@336`、`CANDIDATES_OVERVIEW@337`、`SELECTION_FILE@339`、`REFRESH_SCOPES@346`、`QUOTE_INPUT_CHARS@370`、`TRANSLATION_INPUT_CHARS@371`、`now_utc@464`、`sha256_text@466`、`sha256_obj@467`、`read_json_file@471`、`require_professor_dir_under_program@473`、`truncate@474`、`rel_path@477`、`safe_result_file@479`、`direction_machine_id@480`、`direction_papers@484`、`render_frontmatter@495`、`split_frontmatter@496`、`managed_conflict@497`、`load_input_pack@526`、`load_candidate_state@531`、`strict_candidate_state@533`、`profile_fingerprint@855`、`load_profile_text@864`、`_direction_slices@873`、`_cross_group_fresh@898`、`_parse_direction_id_list@912`、`_parse_cross_groups@922`、`STAGE3_INVOCATION_VERSION@961`。
- 第一批 Stage 3 校验管线的别名（9 个）：`stage3_validation_evidence@1090`、`stage3_correction_scopes@1091`、`stage3_repairable_correction_directions@1092`、`carry_stage3_validator@1093`、`stage3_current_result@1094`、`require_stage3_correction_invariants@1096`、`_write_stage3_invocation@1097`、`_read_stage3_invocation@1098`、`_require_invocation_source@1099`。
- 仍在 runner 的 6 个名字（含别名，不全是 `def`）：`_stage3_args_from_invocation@175`、`validate_candidate_result@1649`、`validate_cross_result@1728`、`render_candidates_md@1792`、`render_candidates_overview@1800`、`canonical_professor_dir@2614`。

最晚的是 `canonical_professor_dir`（2614–2624），因此绑定点放在 2624 之后。

### 为什么绑定点在 Stage 4 代码中间

`_stage3_selected_scope_keys` 用 `canonical_professor_dir`，后者目前仍是 runner 里的共享 helper（Stage 4 的四个函数也用）。要么把 `canonical_professor_dir` 一起搬进共享层（本批不扩范围），要么把绑定点放到它之后（本批选择）。四个别名在 `main()` 运行前建立即可，位置靠后不影响行为；等共享层再把 `canonical_professor_dir` 搬走时，这个绑定点可以随之前移。

## 设计

新模块 `_stage3_commands.py`，一次 `build()`：56 个 keyword-only 参数、4 个成员；加载块锚点取 `SCHEMA = 1`（280）所在行；绑定块插在 `canonical_professor_dir` 结束之后。

### 取舍

1. **把 `canonical_professor_dir` 一起搬**：它是 Stage 4 共享件，塞进 Stage 3 模块会破坏归属，否决。
2. **把 `_stage3_selected_scope_keys` 留在 runner**：那样 Stage 3 还漏一个 helper，且要多注入一个 runner 函数，下一批还得回来搬，否决。
3. **四个一起搬、绑定点后移**（选中）：Stage 3 一次拆完，绑定点位置虽在 Stage 4 区域但语义正确（依赖已就绪）。

## 实施步骤

0. 从干净基线开始：`git checkout e303a1c -- .apm/skills/professor-contact/scripts/`（或 `git status` 确认只有本次改动），删掉工作树里遗留的演练产物，再从 `e303a1c` 的 runner 删除定义；否则第 2 步会“已无定义可删”。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage11/spec-b11.json` 生成模块与 probe runner：模块名 `_stage3_commands`、4 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（280）、`bind_after_line` = 2624、56 个参数名、模块 import（`Path`、`Any`、`json`、`os`、`sys`、`types`）。
2. 删除 4 个定义（按 AST 行区间，四段）；把删除后合并出来的两处空行块（4 行、7 行）收敛为 2；父提交自带的 3 行与 6 行块保持原尺寸。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、四段定义删除；没有常量值、import、CLI、入口清单改动；空行用只读脚本比对。
4. 逐字核对：4 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对；定义内注释用文本比对。
5. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage3-validation`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 4 个名字做 T0–T3，预期 **28 条 `OK`**（T0 3、T1 9、T2 7、T3 9）。
- 行为：`stage3-plan`／`stage3-finalize`／`stage3-rebuild-overview` 与 scoped selection 的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `validate_candidate_result`／`validate_cross_result`／`render_candidates_md`／`render_candidates_overview`／`_stage3_args_from_invocation` | 后续批次；本批按引用注入 |
| `canonical_professor_dir` 与 Stage 4／5／迁移 | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **绑定点必须晚于 `canonical_professor_dir`（2624）**：放早会让 `_stage3_selected_scope_keys` 的闭包参数缺失，导入期 `NameError`。
2. **`cmd_stage3_plan` 与 `cmd_stage3_finalize` 互不直接调用**，但都依赖第一批的 9 个别名；绑定点已在 1049–1086 之后，满足。
3. **四段之间夹着 `_stage3_validation` 的绑定块（1049–1086）**：删除按 AST 定义做，不会碰到绑定块；实施前用 AST 确认四段内只有这 4 个定义。
4. **空行**：删除后合并出 4 行与 7 行两块，需收敛为 2；父提交自带的 6 行块（产物约 3939–3944）必须原样保留；绑定块两侧固定留 2 行（产物 1771–1773 的 3 行块来自插入，不是继承）。
5. **docstring**：4 个定义里 2 个有 docstring（都多行）、2 个没有；核对要读整行摘要。

## 实施前演练

按同一 spec 用 v4 生成、改掉模板里的“Stage-2 helper module”字样（本批是 Stage 3）并手工收敛空行后：模块 1013 行、runner 4712 行；`--help` 与父提交逐字节相同；A/B 28 条 `OK`（T0 3、T1 9、T2 7、T3 9）；docstring `total=4 with_doc=2 multi=2 clean_equal=2 without_doc=2 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 5 个 hunk。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核的非阻断意见修正——R6／风险 4 的空行归属改为“父提交只剩 6 行块、绑定块两侧固定 2 行”、“仍在 runner 的 6 个名字（含别名）”、第 1 步前补“从干净基线 e303a1c 开始”的说明、注明模板里的 Stage-2 字样要改成本批的 Stage 3。

## 审核状态

- 第 1 版：待计划审核。
- 第 2 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
