# 第二批：解除 Stage 5 复制整份 runner 源码执行的机制（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- Test plan revision: 第 2 版。
- 需求来源：负责人 2026-10-18 授权的三批 Stage 重构要求第 2 批；原文见执行计划。
- Target repository revision: 工作分支 `refactor/stage5-runner-invocation`（从 `74bd29b572c1b3f68f230a554f57d0202e54cde8` 拉出）实施后的提交。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本次修改明确要达到的目标与本次直接改变的成功、失败、兼容行为。
- Proposed review status: pending（等待测试计划审核）。
- 唯一规范来源：本文件。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | wrapper 的审计来源标签在三种 polish 取值下不变 | 经 `stage5_immutable.py stage5-finalize` 完成一次 finalize：不传 `--polish-mode`、显式传 `none`（与不传同一代码路径）、传 `dynamic-fields-only` | md 分别含 ` ｜ 过稿: none`、` ｜ 过稿: none`、` ｜ 过稿: humanizer-ja(dynamic-fields-only)`，且都不含 `humanizer-ja(business)`；模板固定段与今天逐字一致 | 复用 `tests/test_stage5_immutable.py::TestStage5ImmutableTemplates` 的 `test_finalize_without_full_body_humanizer_preserves_fixed_segments`、`test_dynamic_field_polish_provenance_is_explicit`、`test_first_and_followup_are_both_rendered_from_stable_templates`（既有断言，不新增） |
| T2 | 直调 runner 的默认渲染字节不变 | 不经过 wrapper，直接 `contact_state.py stage5-finalize`（不传内部参数）完成一次 finalize | md 的审计来源行仍是 ` ｜ 过稿: humanizer-ja(business)`；其余渲染与今天一致 | 新增断言：在 `tests/test_stage5_immutable.py` 中经真实 runner 路径完成一次 finalize，断言 md 含 ` ｜ 过稿: humanizer-ja(business)`，且不含另外两个取值 |
| T3 | 审计标记契约漂移时仍失败关闭 | 把安装布局夹具里的 runner 副本的 `business` 后缀字面量改成别的文本，再经 wrapper 执行 finalize | wrapper 不调用 finalize、不写任何用户文件（教授目录无 md/txt/state），stderr/stdout 返回既有失败 JSON（`status: error`、`reason_code: stage5_provenance_patch_failed`），退出码非 0 | 新增用例：复用 `TestWrapperKeepsInstalledLayoutLocator` 的假安装布局夹具，改坏副本后断言上述四点 |
| T4 | 调用方自带的内部参数不改变审计来源 | 调用方给 wrapper 传 `--audit-provenance business`（不另传 `--polish-mode`） | wrapper 按自己声明的 polish 取值渲染：md 含 ` ｜ 过稿: none`，不含 `humanizer-ja(business)`；调用方的取值不生效，也不出现未知参数错误 | 新增用例：同一 fixture 下传入该选项并断言上述两点，同时断言退出码为 0 |
| T5 | 已安装布局下核验 locator 仍可解析 | wrapper 与 runner 位于 `.agents/skills/professor-contact/scripts/`，checker 位于同级 `professor-collector` skill | finalize 成功、状态记录 `confirmed_cross_source`、不出现 `contact_evidence_check_unavailable` | 复用 `tests/test_stage5_immutable.py::TestWrapperKeepsInstalledLayoutLocator::test_finalize_through_wrapper_certifies_installed_layout_checker`（既有断言，不新增） |
| T6 | 定向单封范围、计划阶段与生成器正文合同不受影响 | wrapper 带 `--email-id` 定向 finalize；`stage5-plan` 直调；生成器角色正文的 Stage-5 合同文本 | 只写选中邮件，其他教授目录与总览字节不变；plan 输出与今天一致；正文仍含 `--polish-mode dynamic-fields-only`、`Do not pass \`--humanized\` or \`--humanized-map\``、`byte-identical`，且该节仍写 “never enters the humanizer” | 复用 `tests/test_stage5_immutable.py::TestStage5ImmutableTargetedScope`、`tests/test_stage5_fixture_isolation.py` 与 `tests/test_stage5_dualtarget_contract.py::test_generator_wrapper_instructions_reject_full_body_inputs`（既有断言） |

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-runner-invocation` 内进行；临时运行产物放仓库外 `/tmp` 目录（本次用 `mktemp -d /tmp/pc-batch2-XXXXXX`）。

1. 准备：确认工作树只有本批改动、测试目录可导入、Python 可用（本批实现先提交，第 5 步记录的 SHA 与被测内容一致）。
   ```sh
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-runner-invocation
   git status --porcelain
   python3 --version
   ```
2. T1、T3、T4、T5、T6 的目标测试文件（第二批改动集中在 wrapper、它的标签契约与被改的生成器正文）：
   ```sh
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-runner-invocation/.apm/skills/professor-contact/tests
   python3 -m unittest test_stage5_immutable test_stage5_fixture_isolation test_stage5_dualtarget_contract -v
   ```
   预期：全部 `ok`，无 `FAIL`/`ERROR`。T2 的断言就在 `test_stage5_immutable` 内，随同一次运行覆盖；T6 引用的生成器正文合同断言在 `test_stage5_dualtarget_contract`。
3. T2 直调默认路径：由第 2 步的新用例覆盖；该用例必须实际以 `sys.executable <runner> stage5-finalize ...` 运行真实脚本，而不是调用 wrapper。
4. 兼容性与既有门禁：把改动推送到 PR 后，仓库 CI（`.github/workflows/ci.yml`）会对该提交跑全量 `unittest discover`；直接引用该运行结果，不在本地重复跑整套。CI 未通过时按第 6 步处理。
5. 记录：保存上述命令、实际提交 SHA、每个编号的通过/失败与必要输出片段到 `/tmp` 运行目录；交付时只列逐项结果与复用来源。
6. 失败处理：
   - 定向用例失败：区分“本次改动引入的回归”“既有失败”“环境问题”；本次改动引入的回归交产品实现负责人修复后重跑受影响编号。
   - 已知与本批无关的既有跳过项（Nix 安装态专用）按未执行记录，不算失败。
   - 连续失败时保留全部尝试，不做无新信息的重复运行。

## 环境与预检

- 使用仓库现有的本地 Python（本次准备时 `python3 --version` 为 3.14.7）与既有测试夹具，不新增依赖、不新增判定器、不新增采集器。
- 测试只使用合成数据与临时目录；`install_issue59_checker` 注入的 `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 由既有夹具在用例结束时恢复，本次不新增环境变量。
- 预检只确认命令可用、工作树干净、必需文件存在；不预先执行业务目标命令求结果。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 相邻模块可被 finalize 子进程导入 | 本批只解除复制这一前提；runner 目前没有相邻业务模块，真正验证在第三批抽 Stage3 渲染模块时进行 |
| 解释器选择与 wrapper 内部写入顺序 | 需求 R3 的两项保持没有业务可观察出口：解释器与命令形状由步骤 2 的运行本身证明可用，“真实脚本路径”一侧面由 T5 覆盖，写入顺序由 T3 的零写入与成功用例的产物覆盖，不单设观察点 |
| 临时副本文件不再产生 | 属于内部实现细节；对外行为由 T1/T2/T5 覆盖，不单独建立观察点 |
| `stage5-plan` 的其余行为、Stage 2/3/4 业务回归 | 本次未修改，按 CI 既有门禁覆盖，不新增清单项 |
| 仓库外消费者是否解析过临时副本文件名 | 不是正式 contract，无法在本仓观察；按执行计划的 unresolved impact 记录 |

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：随执行计划第 2 版调整 T4——执行计划取消了“wrapper 拒绝调用方内部参数”的新行为，改为按既有 `--humanized` 方式丢弃；T4 相应改为“调用方取值不生效、wrapper 声明生效”。其余编号未变。
- 第 3 版：按测试计划审核（第一、二关口 PASS）的三项意见修正：T6 的检查方式补上生成器正文合同断言所在的 `test_stage5_dualtarget_contract`（不新增测试）；T4 用例补 `returncode == 0` 断言（计划原本已写明）；修正审核状态版本号。同时接受可选记录精度意见：T1 注明“不传”与“传 none”同一路径、把解释器与写入顺序为何不单设观察点补进不纳入表、第 1 步写明先提交再记录 SHA。

## 审核状态

测试计划第 3 版为当前唯一版本；第 2 版已取得第一关口与第二关口 PASS（无 blocker），本版只落实该轮意见中的表述与断言归属，未增删必测项。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
