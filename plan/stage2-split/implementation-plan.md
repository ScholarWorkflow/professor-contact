# Stage 2 划分第一批：把预检、身份与 plan 命令层抽成内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-20 在本仓库会话中的指示：

  > 你先不管92，它的修复有问题。你基于当前主分支对stage2进行划分。

  即：不再等待 PR #92，以当前 `main` 为基线拆分 Stage 2；每个批次独立提交 PR，按执行计划、测试计划与正式审核推进；运行行为不变。
- Requirement revision: 第 1 版（2026-10-20 的 Stage 2 划分指示；延续 2026-10-18 三批 Stage 重构要求中的“抽组不改行为、保留旧接口、不顺便改格式”原则）。
- Canonical Plan revision: 第 2 版（第 1 版经 2026-10-20 计划审核批准；第 2 版只并入该轮非阻断建议，语义未变）。
- Target repository revision: `b5621db5cb136de11d64296fb9a4d0b43e2ed9a6`（`main`，PR #102 合并后；runner 11894 行）。本批工作分支 `refactor-stage2-split` 从该提交拉出。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、代理入口、安装布局或 CLI 变化。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`；独立计划审核于 2026-10-20 给出，P1–P4 全 PASS，无 blocker，五条非阻断建议已并入第 2 版；Review record 见本文件末节）。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## Stage 2 总体划分（本批位置）

Stage 2 是 runner 里剩余最大的一块：52 个名字含 `stage2` 的函数、2 个上下文类、2810 行（另加只被 Stage 2 使用的私有 helper）。一次搬完不可审，按职责与依赖顺序分成 6 批，每批一个 PR：

说明：开头“2810 行”只统计 52 个名字含 `stage2` 的函数与 2 个上下文类；批次表里的“代码行”会额外计入只被 Stage 2 使用的私有 helper（例如 `_compute_paper_direction_affinity`、`validate_resolve_results`、`_pack_resolved_grouping`），所以各批相加大于 2810。

| 批次 | 新模块 | 函数数 | 代码行 | 内容 |
| --- | --- | --- | --- | --- |
| 1（本批） | `_stage2_preflight.py` | 27 | 约 801 | 预检输入与身份、artifact 守卫、pack 指纹、validator 接受判定、`stage2-preflight` 与 `stage2-plan` 命令 |
| 2 | `_stage2_resolve.py` | 16 | 约 760 | 候选识别、resolve 模型输入、`stage2-resolve-plan` 命令、运行指纹 |
| 3 | 追加到 `_stage2_resolve.py` | 7 | 约 585 | resolve 结果校验、证据证明、`stage2-resolve-finalize` 与 `stage2-resolve-accept` |
| 4 | `_stage2_finalize.py` | 7 | 约 811 | finalize 预检漂移、渲染状态、`stage2-finalize` 命令 |
| 5 | `_stage2_validation.py` | 16 | 约 871 | 校验报告、后续论文渲染、`stage2-refine-*` 与 `stage2-record-validation` |
| 6 | `_stage2_context.py` | 2 类 + 事实层 | 约 900 | `Stage2Context` / `Stage2PackRefineContext` 与 facts／pack 渲染闭包 |

选择这个顺序的理由：

- 第 1 批只依赖 runner 的通用原语（错误通道、sha、读 JSON、路径归属）；上下文类本批不搬，只在 `cmd_stage2_plan` 里以注入值构造，所以本批是风险最小、又能先确立“Stage 2 内部模块 + 显式注入”模式的起点。
- 第 2、3 批按 resolve 的“计划 → 提交”切分：计划层只读 facts 并产出 job，提交层校验外部结果并写 state，两段的失败方式不同，分开审核。
- 第 4 批是本块最大的单函数（`cmd_stage2_finalize`，599 行），单独成批，避免与其它流程混做。
- 第 5 批的校验与 refine 共用同一组“后续论文/校验报告”helper，天然一块。
- 第 6 批最后做：两个上下文类的方法体直接引用约 20 个 runner helper，方法不构成闭包，不能用本批的工厂注入方式逐字搬；需要先看清被前五批留下的事实层归属，再单独设计。其方案在本批只登记边界，不在本批实施。

前五批完成后，Stage 2 的 9 个命令、全部 stage2 命名的 helper 与 resolve／finalize／校验流程都在独立模块里；runner 只剩第 6 批的上下文类、facts 装载与 pack 渲染层。本批不承诺第 2–6 批的细节，它们的执行计划各自另立文件。

## 正式需求与范围

- **R1 划分**：把本批 27 个函数原样移入新内部模块 `_stage2_preflight.py`，`contact_state.py` 保留同名同签名的模块级入口。
- **R2 行为不变**：相同输入产生逐字节相同的 JSON 输出、文件写入、退出码与失败原因码；不改变任何校验、指纹或顺序。
- **R3 依赖显式**：新模块不 import runner，不修改 `sys.path`，不注册 `sys.modules`；它需要的 runner 名字全部以显式参数注入，模块内不出现第二份实现。
- **R4 加载方式**：沿用仓库既有内部模块做法（`Path(__file__).with_name(...)` + `importlib.util.spec_from_file_location` + `module_from_spec` + `exec_module`），保证 runner 无论是直接执行还是被测试按文件路径加载都能找到相邻模块。
- **R5 兼容面**：`contact_state.<被搬函数>`、`contact_state.STAGE2_PREFLIGHT_VERSION` 等模块级名字、CLI 子命令（含 `stage2-preflight`、`stage2-plan`）、七个薄入口与测试调用点都不改。

**非目标**：不改任何业务逻辑、校验规则、指纹算法、schema、常量值或 Markdown；不改 resolve／finalize／refine／上下文类（第 2–6 批）；不改测试断言与测试名称；不改七个入口清单与 Nix 安装布局；不动共享错误通道、事务／回滚与 Stage 3–5 代码；不顺手修复本块内已存在的死代码（例如 `Stage2PackRefineContext.narrative_later_keys_for` 的重复定义）。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。以下行号均指 `b5621db` 的 `scripts/contact_state.py`。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 本批 27 个函数 | identities：`stage2_preflight_versions` 3196-3208、`stage2_preflight_params` 3211-3215、`stage2_target_fingerprint` 3218-3237、`stage2_candidate_fingerprint` 3240-3263、`stage2_candidate_universe` 3266-3284、`stage2_papers_catalog_view_fingerprint` 3287-3310、`stage2_authorship_ledger_view_fingerprint` 3313-3337、`stage2_program_inputs` 3340-3350、`stage2_target_path` 3353-3355、`read_stage2_target` 3358-3377；local identity：`stage2_local_identity` 3441-3464、`stage2_transaction_identity` 3467-3475、`stage2_preflight_cheap_inputs` 3478-3507；guards：`stage2_artifact_guard` 3510-3513、`stage2_artifact_guard_reason` 3516-3534、`_artifact_guards_for_keys` 3537-3570、`stage2_direction_artifact_guards` 3573-3581、`stage2_resolution_evidence_guards` 3584-3594；pack 分组：`_pack_resolved_grouping` 3597-3624；freshness/metadata：`stage2_freshness_view_fingerprint` 3627-3641、`stage2_preflight_metadata` 3644-3719；pack 指纹与 validator：`stage2_pack_state_fingerprint` 3722-3727、`stage2_pack_content_fingerprint` 3730-3731、`stage2_validator_accepts` 3734-3777；命令：`cmd_stage2_preflight` 3780-3987、`stage2_plan_bind_preflight` 3990-4015、`cmd_stage2_plan` 4018-4109 | `scripts/contact_state.py` |
| 三个 Stage 1 helper 不搬 | `stage1_state_path` 3380-3382、`read_stage1_professor_entry` 3385-3425、`_canonical_under` 3428-3438 位于本批区间中间，但它们是通用的 Stage 1 状态读取/路径归属 helper：测试直接调用 `read_stage1_professor_entry`，且不属于 Stage 2 预检语义。它们留在 runner，以显式参数注入新模块 | `tests/test_stage2_preflight.py:312`；对全仓的引用检索 |
| 组外调用点很少且都在命令之后 | runner 里除本批自身外只有：`stage2_finalize_preflight_plan` 4782/4788 调 `stage2_target_path`、`read_stage2_target`、`stage2_preflight_cheap_inputs`；`cmd_stage2_finalize` 5482/5510/5519 调 `stage2_preflight_metadata`、`stage2_pack_content_fingerprint`；`stage2_bound_render` 10157、`stage2_validation_report` 10398 调 `stage2_pack_state_fingerprint`；`stage2_require_recorded_validation` 10595、`cmd_stage2_refine_finalize` 10928、`cmd_stage2_record_validation` 10974/11011 调 `stage2_pack_content_fingerprint`；`build_parser` 11615/11626 引用两个命令 | 对 AST 的组外引用统计 |
| 测试直接调用本批 7 个入口 | `test_stage2_preflight.py` 303/308/309 调 `stage2_preflight_params`、`read_stage2_target`、`stage2_preflight_metadata`，345 行调 `cmd_stage2_preflight`；`test_stage2_style_validation_handoff.py` 420/481/504/1242 调 `stage2_pack_state_fingerprint`／`stage2_pack_content_fingerprint`；`test_contact_state.py` 3047/3054/3061/3179 调两个命令；`test_stage1_handoff_identity.py:341`、`test_issue65_gate2_r24_regressions.py:28` 调 `cmd_stage2_preflight`；`test_stage2_preflight.py:628` 与 `test_resolved_direction_preflight_integration.py:199/213`、`test_stage2_style_validation_handoff.py:479` 引用 `STAGE2_PREFLIGHT_VERSION`／`STAGE2_RESOLUTION_SEMANTICS_VERSION` | 上述测试文件 |
| 没有 import 期引用 | 全模块没有在默认参数、装饰器、类体或模块级表达式中引用本批 27 个函数或 8 个待搬常量；因此把入口定义位置改到 `_canonical_under` 之后（3438 行附近）不会改变导入行为 | 对顶层语句与默认参数的 AST 检索（证据见测试记录） |
| 8 个常量只被本批与本块外的 Stage 2 代码引用 | `STAGE2_PREFLIGHT_VERSION`（256）、`STAGE2_RESOLUTION_SEMANTICS_VERSION`（269）、`FACTS_GENERATOR_VERSIONS`（255）、`SIDECAR_EXTRACTOR_VERSIONS`（241）、`STAGE2_TARGET_FILE_NAME`（270）、`AUTHORSHIP_LEDGER_FILE`（274）、`STAGE2_GUARD_KINDS`（276）、`PAPER_ANALYSIS_SCOPES`（275）；块外引用只有 `load_sidecar` 1243、`load_facts_sidecar` 1319、`stage2_pack_requires_membership_rebuild` 4822，都是 Stage 2 自身代码，运行时调用，不依赖定义行先后 | `scripts/contact_state.py` |
| 相邻模块既有加载做法 | `_stage3_render` 35-41、`_contact_io` 48-54、`_contact_evidence` 73-80、`_stage3_handoff` 158-164 都用 `Path(__file__).with_name(...)` + `spec_from_file_location` + `module_from_spec` + `exec_module` | `scripts/contact_state.py` |
| 测试夹具按通配复制内部模块 | 两个把 runner 复制到假安装布局的夹具用 `sorted(RUNNER.parent.glob("_*.py"))` 复制相邻模块，新模块自动被带上 | `tests/test_stage5_immutable.py:220`、`tests/test_stage5_dualtarget_contract.py:331` |
| Nix 按整树复制 | runtime 派生 `cp -R .apm/skills/professor-contact/.` 后只改七个入口的 shebang；新内部模块随整树进入安装，`entryNames` 不变 | `nix/contact.nix:124-152` |
| 内部模块不进公开入口清单 | `SKILL.md` 的七个入口清单与 `nix/contact.nix` 的 `entryNames` 只列薄入口；`_stage2_chatgpt_handoff_impl.py`、`_stage3_render.py` 等同样不在清单里 | `SKILL.md:170`、`nix/contact.nix:124-131` |
| 测试不重绑本批依赖 | 测试只 patch `contact_state.os` 的属性（`os.replace`／`os.open`／`os.write`／`os.read`），没有对 `fail`、`emit`、`soft_exit`、`read_json_file`、`sha256_*`、`direction_machine_id` 等函数做赋值或 `patch.object`；因此按加载时绑定这些函数不会改变测试里的可观察行为 | 对 `tests/` 的检索 |
| runner 现在以自己的路径执行 | 第二批已解除“复制整份 runner 到临时目录执行”；`stage5_immutable.py` 不再复制 runner，相邻模块可按 `__file__` 解析 | 已合并 PR #97；`scripts/stage5_immutable.py` |
| Python 版本 | CI 为 ubuntu / Python 3.12；本地 3.14.7；闭包与关键字参数在两者上行为一致 | `.github/workflows/ci.yml` |

## 方案

### 因果链

需求（Stage 2 需要按边界拆出 runner）→ 现行机制（预检/身份/守卫/plan 命令共 27 个函数散在 runner 3196-4109，依赖 runner 的错误通道、sha、读 JSON、路径归属、facts 校验与上下文类）→ 变更点（把这 27 个函数原样移入同目录内部模块，模块用工厂函数在加载后一次性接收 runner 的名字；runner 在依赖全部定义之后建立模块命名空间并保留同名入口）→ 行为变化（用户可见输出、校验、指纹、CLI 全部不变；runner 少 800 行，多一个内部模块与一段加载/绑定代码）→ 满足需求。

### 选定设计

**新模块 `scripts/_stage2_preflight.py`**（下划线前缀沿用既有内部模块约定）：

- 文件头：`from __future__ import annotations`、`import json`、`from datetime import datetime`、`from pathlib import Path`、`import types`。
- 模块级只定义本批搬走的 8 个常量（值逐字照搬）：`SIDECAR_EXTRACTOR_VERSIONS`、`FACTS_GENERATOR_VERSIONS`、`STAGE2_PREFLIGHT_VERSION`、`STAGE2_RESOLUTION_SEMANTICS_VERSION`、`STAGE2_TARGET_FILE_NAME`、`AUTHORSHIP_LEDGER_FILE`、`PAPER_ANALYSIS_SCOPES`、`STAGE2_GUARD_KINDS`。
- 模块主体是一个工厂：

  ```python
  def build(*, fail, soft_exit, emit, read_json_file, sha256_obj, sha256_bytes,
            sha256_text, split_frontmatter, direction_machine_id, facts_direction_id,
            direction_relevant_keys, gap_scope_keys, read_stage1_professor_entry,
            stage1_state_path, _canonical_under, load_input_pack, load_freshness_cache,
            _resolve_evidence, Stage2Context, filename_component, truncate,
            INPUT_PACK, GAP_SCOPES, FRESHNESS_SCOPES, ANALYSIS_MD, MANAGED_BY,
            SHORTLIST_MAX, ABSTRACT_INPUT_CHARS, QUOTE_INPUT_CHARS,
            TRANSLATION_INPUT_CHARS):
      # 27 个函数逐个原样搬入这里（内容不变，只是缩进进工厂作用域）
      ...
      return types.SimpleNamespace(stage2_preflight_versions=stage2_preflight_versions, ...)
  ```

  参数名与函数体里原来的自由名字**逐字同名**（包括 `_canonical_under`、`_resolve_evidence`、`Stage2Context` 这些带下划线或类名前缀的名字），所以 27 个函数的函数体（含内部互调）逐字不变；内部互调由闭包直接解析到同一个工厂作用域，不需要在每个调用点重复传参。这也避免了“每个函数各带一长串关键字参数、38 处内部调用逐个补注入”的编辑面。

**runner 侧加载与绑定**：

- 顶部（与 `_stage3_render` 等并列）用按路径方式加载模块文件，得到 `_stage2_preflight_module`。
- 在 `_canonical_under`（3428-3438）之后、原 `stage2_local_identity` 的位置调用一次工厂，传入 runner 自己的函数对象与常量：

  ```python
  _stage2_preflight = _stage2_preflight_module.build(
      fail=fail, soft_exit=soft_exit, emit=emit, read_json_file=read_json_file,
      sha256_obj=sha256_obj, sha256_bytes=sha256_bytes, sha256_text=sha256_text,
      split_frontmatter=split_frontmatter, direction_machine_id=direction_machine_id,
      facts_direction_id=facts_direction_id, direction_relevant_keys=direction_relevant_keys,
      gap_scope_keys=gap_scope_keys, read_stage1_professor_entry=read_stage1_professor_entry,
      stage1_state_path=stage1_state_path, _canonical_under=_canonical_under,
      load_input_pack=load_input_pack, load_freshness_cache=load_freshness_cache,
      _resolve_evidence=_resolve_evidence, Stage2Context=Stage2Context,
      filename_component=filename_component, truncate=truncate,
      INPUT_PACK=INPUT_PACK, GAP_SCOPES=GAP_SCOPES, FRESHNESS_SCOPES=FRESHNESS_SCOPES,
      ANALYSIS_MD=ANALYSIS_MD, MANAGED_BY=MANAGED_BY, SHORTLIST_MAX=SHORTLIST_MAX,
      ABSTRACT_INPUT_CHARS=ABSTRACT_INPUT_CHARS, QUOTE_INPUT_CHARS=QUOTE_INPUT_CHARS,
      TRANSLATION_INPUT_CHARS=TRANSLATION_INPUT_CHARS)
  ```

  工厂参数名与旧自由名完全一致，函数体不需要任何改名；`stage2_plan_bind_preflight` 的注解因 `from __future__ import annotations` 仍是字符串，也不受影响。

- 绑定后立刻建立 runner 命名空间的同名入口：27 个函数一律 `stage2_xxx = _stage2_preflight.stage2_xxx`（无包装函数，签名与函数对象都是搬走前同一个），8 个常量 `STAGE2_PREFLIGHT_VERSION = _stage2_preflight_module.STAGE2_PREFLIGHT_VERSION` 等。
- 原 3196-3377、3441-3777、3780-4109 的 27 个定义删除；`stage1_state_path`／`read_stage1_professor_entry`／`_canonical_under` 三个 helper 原地保留。
- runner 里其它调用点（4782、4788、5482、5510、5519、10157、10398、10595、10928、10974、11011、11615、11626）一行不改。

**为什么用工厂闭包而不是逐函数关键字注入**：

- 27 个函数、30 个 runner 依赖、38 处内部互调。逐函数注入需要改动每一处内部调用（把 `f(x)` 改成 `f(x, sha256_obj=sha256_obj, ...)`），编辑面大，且任何一处漏传只会在运行到该分支时暴露。
- 闭包绑定让函数体保持逐字不变（只增加缩进），可以用 AST 对比机械证明“搬移没有改逻辑”；内部互调不需要人工补参。
- 依赖在 runner 加载时一次性求值，缺一个参数立刻 `TypeError`（导入即失败），不会等到某个分支才暴露。
- owner 仍是 runner：错误通道、sha、读 JSON、路径归属、facts 校验、上下文类都留在 runner；模块只保存指向同一对象的引用，不复制实现、不新建通道。

**替代方向与取舍**：

| 方向 | 不采用的原因 |
| --- | --- |
| 逐函数关键字注入（沿用前三批做法） | 27 个函数、40 余处内部调用都要补参；编辑面与漏传风险都高于闭包绑定，且无法用“函数体逐字不变”证明搬移安全 |
| 新模块 `import contact_state` 取依赖 | 循环导入；测试按文件路径加载 runner，`contact_state` 不一定在 `sys.modules` |
| 加载后给模块属性赋值或 `configure()` 全局变量 | 隐式全局状态，签名上看不到依赖，模块无法独立测试；与既有内部模块的显式注入约定冲突 |
| 在模块里复制 `sha256_*`、`read_json_file` 等实现 | 出现第二份实现，行为与常量可能漂移；直接违反 R3 |
| 把三个 Stage 1 helper 一起搬走 | 它们不是 Stage 2 语义，测试直接调用 `read_stage1_professor_entry`；搬走会扩大本批范围并制造无谓的跨批依赖 |
| 把 8 个常量留在 runner 再注入 | 这些常量只被 Stage 2 代码引用（块外三处也是 Stage 2）；搬进模块并由 runner 别名，避免“常量既在 runner 又在模块”的重复定义 |
| 一次搬完整 Stage 2 | 2810 行 + 2 个类，无法逐项审核；按 6 批分，每批有独立失败方式与测试面 |

### 冻结的契约

- 27 个函数的名字、参数列表、默认值、返回结构与副作用不变；runner 入口是同一个函数对象，不是包装函数，因此 `inspect.signature` 也不变。
- 8 个常量的类型与值不变；runner 与模块引用同一个对象。
- 错误通道只有 runner 的一份：模块通过注入的 `fail`／`soft_exit`／`emit` 调用，不导入 `_contact_io`，不新建业务通道。
- CLI 子命令（`stage2-preflight`、`stage2-plan`）与七个入口清单不变。
- 模块文件是内部辅助模块：不进 `SKILL.md` 入口清单，不改 `entryNames`，不改任何文档枚举。

## 影响

- **intended_change**：27 个函数从 `contact_state.py` 移入 `_stage2_preflight.py`；runner 增加按路径加载、一次工厂绑定与 27 个同名别名、8 个常量别名；8 个常量定义随函数移入模块。
- **preserved_behavior**：`stage2-preflight` 与 `stage2-plan` 的 stdout JSON（字段、顺序、值）、失败原因码与退出码；预检指纹、pack 指纹、validator 判定；`cache.preflight` 的写入结构；`Stage2Context` 的行为；所有测试调用点；fixture 复制的 runner 行为；Nix 安装树的内容与七个入口。
- **approved_behavior_change**：无。
- **prohibited_side_effect**：修改任何函数逻辑、常量值、指纹算法、schema、输出字段或排序；修改测试断言或测试名称；复制 runner helper 的实现；新建第二个错误通道或业务通道；改 CLI、入口清单或安装布局；顺手搬动 resolve／finalize／refine／上下文类；在 runner 里改 `sys.path` 或注册 `sys.modules`。
- **unresolved impact**：
  1. 仓库外若有人按“scripts 目录文件清单”做打包或审计，会多看到一个内部模块；这与已合并的 `_stage3_render.py` 等五个内部模块同一性质，不改变入口契约，不阻塞本批。
  2. 27 个函数对象的 `__module__` 变为 `_stage2_preflight`、`__qualname__` 变为 `build.<locals>.<name>`；仓内没有消费者依赖这两个属性（无 `inspect`／`__qualname__` 检索命中），调用、签名与行为不受影响。
  3. 第 6 批搬 `Stage2Context` 时必须同步更新本批工厂的注入点（否则闭包仍持有旧的类对象）；这是排序依赖，写入第 6 批计划即可，不影响本批。

## 关键安全条件与反例

必须一直成立的条件：

1. 27 个函数的 AST（参数、函数体、返回）与搬移前逐字等价；除缩进外不允许任何改动。
2. runner 无论直接执行还是被测试按路径加载，都能加载 `_stage2_preflight.py`，且工厂只调用一次。
3. 工厂参数覆盖 27 个函数引用的全部 runner 名字；缺一个就在导入期 `TypeError`，不允许静默回退到模块全局。
4. `contact_state.<函数>` 与 `contact_state.<常量>` 的名字、签名、对象身份保持可用；所有既有调用点不改。
5. 错误通道仍只有 runner 的一份；模块不导入 `_contact_io`，不产生第二份业务通道。
6. 8 个常量只定义一次（在模块里），runner 只别名，不复制值。
7. 测试夹具复制 runner 时自动带上新模块（既有 `glob("_*.py")`），不需要改夹具。

代表性反例：

- 工厂在 `_canonical_under`／`read_stage1_professor_entry` 定义之前调用 → 导入期 `NameError`。绑定位置固定在 `_canonical_under` 之后；由“直接执行 runner 的 `--help`／完整测试套件”覆盖。
- 某个函数体引用了未列入工厂参数的名字（例如 `gap_scope_keys` 只在一处用到）→ 调用时 `NameError`。由完整套件与逐个函数的自由名清单覆盖。
- 模块内出现第二份 `fail` 或 `sha256_obj` → 业务失败通道分裂或哈希漂移。由“模块不导入 `_contact_io`、不定义同名 helper”的实现约束与源码检索覆盖。
- 把别名写成包装函数且漏传某个参数 → 行为变化。本方案明确用同一函数对象别名，不做包装。
- 测试在导入后重绑 `contact_state.sha256_obj` → 闭包仍用旧对象。已确认测试没有这种重绑；该约束写入本文件，后续若出现同类测试需改为注入点而不是重绑 runner 名字。
- 常量既留在 runner 又在新模块定义 → 两处可能漂移。本方案要求常量只在新模块定义，runner 别名；由源码检索覆盖。
- 夹具只复制 `contact_state.py` → 复制出的 runner 导入期找不到相邻模块。既有两个夹具已按 `glob("_*.py")` 复制；本批新增的模块自动包含，不需要改夹具。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   1. 新建 `scripts/_stage2_preflight.py`：常量 + `build(...)` + 27 个函数原样搬入 + 返回命名空间。
   2. 在 `contact_state.py` 顶部加载模块；在 `_canonical_under` 之后调用 `build(...)` 并建立 27 个函数别名与 8 个常量别名；删除原 27 个定义；保留三个 Stage 1 helper。
   3. 对本批函数做 AST 对比（搬移前后函数体 dump 相同）、常量值对比、组外调用点清单对比。
3. **测试计划工程师**：按 `Test Engineer Rule.md` 在 `plan/stage2-split/test-plan.md` 写必测清单与三步 recipe。
4. **本地测试工程师**：执行测试计划，结果写入 `plan/stage2-split/test-execution-<date>.md`。
5. **实现符合性审核**（M2）与 **合并审核**（M3）按 `Merge Reviewer Rule.md` 另做。

## 记录（待补）

- 计划审核意见与结论：待补。
- 测试记录：`plan/stage2-split/test-execution-<date>.md`。
- AST／常量／调用点对比的临时证据：放仓库外 `/tmp`，记录里写明路径与摘要。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：并入 2026-10-20 计划审核的五条非阻断建议，不改变任何语义或范围：① 把“不依赖上下文类的行为”改为“上下文类不搬、只以注入值构造”；② unresolved impact 补记函数 `__module__`／`__qualname__` 变化与第 6 批注入点同步依赖；③ R5 把“CLI 七个子命令”改为“CLI 子命令、七个薄入口”；④ 批次表前补“2810 行”与批次代码行的口径说明；⑤ 测试直接调用入口计数由 6 改为 7。

## 审核状态

- 计划审核：`Plan conclusion: APPROVED`（2026-10-20，独立计划审核代理；P1–P4 全 PASS，`Gate review completeness: COMPLETE`，`Required modifications: N/A`，五条非阻断建议已并入第 2 版）。
- 审核结论覆盖：requirement 第 1 版、Plan 第 1 版、目标 revision `b5621db`。第 2 版只并入非阻断措辞与影响补记，未改变 owner、机制、change point、契约或范围，按 `Plan Reviewer Rule.md` 6.3/6.4 复用同一 PASS。
- 测试计划与执行：见 `plan/stage2-split/test-plan.md` 与 `test-execution-<日期>.md`（待写）。
