# 方向真实素材：测试计划

- Test plan revision: TP1.5；2026-10-28；对应 [EP1.2/R1](execution-plan.md)。
- Target repository baseline: ScholarWorkflow/professor-contact `b67dd3ca4d29dfc78f57988564b219c71b582674`。
- Proposed review status: pending。测试资产与可执行 recipe 已按本计划准备；产品新能力尚未实现，T1–T6 全部未执行，不声明 PASS。原 TP1.1 的无关必测项结论可复用；T4 已按验收决定人的本轮精简改写；T5 旧包夹具已按第二关意见改为还原旧字段结构与旧版 `source_hash`。第二关仅待定向复核 T5；第三关未执行。
- 本文件是唯一完整测试计划与步骤承载位置，不另建问卷评估、采集器、判定器或证据账本。

## 1. 唯一必测清单（验收上限）

| 编号 / 业务目标 | 输入或场景 | 预期结果 | 一个足够的检查入口 |
| --- | --- | --- | --- |
| T1 补问只针对缺少的真实方向素材 | 人工读 selection/coordinator/generator 的完整新合同：已选方向但无可用素材；已有可用回答；用户说没有经历或暂不补充 | 缺素材才少量询问实际接触，不固定题数/研究答题；已有材料不重复；Codex needs_input 返回、真人回答后 fresh 委派；OpenCode沿用question；无selection旧路径不变；不捏造经历、不写profile | 独立人工静态核对上述合同及实际待答/恢复分支的字段接线，记录具体位置。只证明规则与接线，不声称真实模型必然自然或每次遵循；不新增强制模型eval |
| T2 正常保存与同方向复用 | 一个隔离合成教授、两个canonical方向、已选idea；保存方向A用户原回答，然后同方向换idea/重编译；模拟取消选择后再次选择 | question/answer不被总结改写；有稳定来源ID；独立文件保留，非profile/note/state权威；取消/重新选择不删除；只冻结所选方向素材，方向B不带入；profile/Stage3状态不变 | producer现有Python unittest框架，经正式素材保存及Stage4入口读取目标JSON/文件，使用直接断言。最小正常序列，不另跑安装或模型同义重复证明 |
| T3 精确来源贯通并拒绝不存在的素材引用 | 正常冻结包与合法三项model JSON，其中①引用方向A的一条素材；再将来源换为未冻结/其他方向素材ID | plan含该原回答；生成/validator使用同一冻结字段；合法引用被接纳并显示准确来源；非法引用拒绝且已有邮件不改；③仍须gap，不能用素材代替 | 扩展现有Stage5 immutable测试路径的定向方法，通过plan→finalize及必要现有validator合同人工核对；用合成模型JSON测输入合同，不冒充真实模型体验 |
| T4 素材更新后重新生成且仅刷新相关邮件 | 邮件A已冻结；修改A回答后用未更新的旧包尝试plan/finalize；经Stage4重新冻结，再用新包运行Stage5计划、构造本轮合成模型结果与草稿并完成邮件；另改未选方向B | 未刷新的旧包提示needs_refresh且不覆盖已有邮件；Stage4的新包与Stage5的model_input包含更新后的原回答，A的source_hash随之改变；本轮结果和草稿可完成新邮件；无关B不改变A的source_hash；profile/Stage3不写不重跑 | 沿用同一个隔离producer集成测试序列，通过Stage4→stage5-plan→本轮合成结果→草稿→finalize检查新输入与输出。生成器重新取本轮输入的工作约定在T1既有静态阅读中检查，不新增真实模型测试或旧模型结果指纹拒绝用例 |
| T5 新旧包的直接兼容 | 旧包无素材字段且相应live素材为空；随后给其方向新增素材；新包原有素材文件被移走 | 无素材旧包保持原行为，无全量重生；新增素材后旧包须Stage4冻结；新包失去原素材被识别变化，不继续引用；现有邮件不批量改写 | 同一Stage5定向测试入口，用合成旧包与临时目录直接验证上述条件，不扩历史全版本迁移 |
| T6 新保存入口防错归属/覆盖 | 保存输入绑定另一方向/教授或旧摘要；已有素材文件不可解析 | 明确拒绝该次写入、原数据不变，不把坏文件当空库覆盖；同名方向不能跨教授自动认同。此项不穷举路径/锁故障；互斥设计按源码审查确认 | 新保存入口的定向unittest负向场景；原文件内容和返回值足够，不另造并发压力/崩溃测试框架 |

T1规则观察不是模型行为实测；T2–T6合成数据验证正式产品入口的确定性行为，不用手工补写email-pack替代被测冻结。仅兼容输入T5可以准备旧格式夹具。fixture/model JSON是明确测试输入，不替代产品传递原回答。

## 2. 可执行 recipe（本轮已准备；实现落地后执行）

本节是可执行的唯一 recipe。测试代码已按本表写好；产品入口尚未实现，因此本轮只记录未执行，不代表第二关或第三关通过。

| 项目 | 本轮固定值 |
| --- | --- |
| 受测仓库 | `ScholarWorkflow/professor-contact`，从 `main` 的 `b67dd3c` 之后的产品实现提交检出；执行时用 `git rev-parse HEAD` 记录实际提交 |
| 测试模块 | `.apm/skills/professor-contact/tests/test_direction_materials.py`（新增 8 项） |
| 解释器 | `/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`（Python 3.14.7）。该路径不存在时改用本机已装的 Python 3.12+，并在执行记录写明实际路径 |
| 工作目录 | 起始于受测 checkout 仓库根目录；执行步骤 1 的 `cd` 后进入 `.apm/skills/professor-contact/tests` |
| 隔离目录 | `RUN=$(mktemp -d /tmp/contact-direction-materials.XXXXXX)`；`TMPDIR="$RUN/tmp"`，所有合成教授、素材、邮件和状态只落在该目录下 |
| 外部依赖 | 无。不读真实 profile/邮件/用户素材，不连 Zotero、浏览器、MCP，不需要安装、模型 provider 或 eval 服务 |
| 素材保存入口 | `contact_state.py direction-materials-save`（EP1.1 的拟名；实现可一致重命名，重命名时本表与测试模块须在同一提交内同步） |
| 素材文件 | `<教授目录>/方向素材.json`，schema 1；`directions[<direction_id>]` 为条目列表或映射，每条含 `material_id`、`question`、`answer` |
| 素材来源 ID | `direction_material:<direction_id>:<material_id>`，须出现在该 email 的 `allowed_sources` |
| 冻结字段 | 邮件包每条 email 的 `direction_materials[]`（含 `direction_id`、`material_id`、`question`、`answer`）；stage5-plan 的 `model_input.direction_materials`。模型结果无需新增素材指纹字段 |
| 新鲜度 | 素材切片变化后 `stage5-plan`/`stage5-finalize` 返回 `status=needs_refresh`，邮件、纯文本与状态文件字节不变 |
| 保存入口输出 | `status=ok`、`material_id`、`materials_file`；拒绝时非零退出码且原文件字节不变 |
| 保存入口标志 | `--program-root`、`--professor-dir`、`--direction-id`、`--answer`、可选 `--question`、`--material-id`、`--expected-sha256`、`--expect-missing` |

必测目标到测试方法的唯一映射（模块共 8 项）：

| 目标 | 测试方法 |
| --- | --- |
| T2 正常保存 | `DirectionMaterialsSaveTests.test_t2_saved_answer_is_frozen_for_the_selected_direction_only` |
| T2 同方向复用与取消选择 | `DirectionMaterialsSaveTests.test_t2_selection_changes_do_not_delete_saved_materials` |
| T3 合法引用 | `DirectionMaterialsProvenanceTests.test_t3_frozen_material_reference_is_accepted_and_rendered` |
| T3 非法引用与 ③ 仍须 gap | `DirectionMaterialsProvenanceTests.test_t3_unfrozen_material_cannot_be_cited` |
| T4 更新后重冻并使用新结果 | `DirectionMaterialsFreshnessTests.test_t4_answer_update_requires_a_stage4_refreeze` |
| T5 无素材旧包兼容 | `DirectionMaterialsCompatibilityTests.test_t5_pack_without_materials_keeps_old_behavior` |
| T5 素材被移走 | `DirectionMaterialsCompatibilityTests.test_t5_removed_material_is_a_slice_change` |
| T6 保存入口防错归属/覆盖 | `DirectionMaterialsSaveGuardTests.test_t6_save_rejects_foreign_binding_and_stale_digest` |

T1 无自动测试方法：由独立 reviewer 一次静态阅读实现后的 selection/coordinator/generator 合同与 `pending_materials` 接线，包括素材更新后 generator 重新取 Stage5 计划及重新生成结果的工作约定，记录具体文件与字段位置。

下列命令从受测 checkout 仓库根目录开始，在同一个 Bash 会话中依次运行；步骤 1 切换目录后，步骤 2 与单项复跑沿用该目录及已设置的变量。

1. 正式执行前先确认受测版本包含测试模块与产品入口：

```bash
set -o pipefail
RUN=$(mktemp -d /tmp/contact-direction-materials.XXXXXX)
mkdir -p "$RUN/tmp"
export TMPDIR="$RUN/tmp"
PYTHON=/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3
"$PYTHON" --version 2>&1 | tee "$RUN/python-version.txt"
git rev-parse HEAD 2>&1 | tee "$RUN/tested-commit.txt"
git cat-file -e HEAD:.apm/skills/professor-contact/tests/test_direction_materials.py
cd .apm/skills/professor-contact/tests
"$PYTHON" -B - <<'PROBE' 2>&1 | tee "$RUN/save-entry-present.txt"
import argparse, importlib.util, sys
spec = importlib.util.spec_from_file_location("cs", "../scripts/contact_state.py")
module = importlib.util.module_from_spec(spec)
sys.modules["cs"] = module
spec.loader.exec_module(module)
for action in module.build_parser()._actions:
    if isinstance(action, argparse._SubParsersAction):
        print("direction-materials-save" in action.choices)
        break
PROBE
```

2. 运行全部 8 项：

```bash
"$PYTHON" -B -m unittest -v test_direction_materials 2>&1 | tee "$RUN/direction-materials.out"
```

单项复跑使用同一解释器与工作目录，例如：

```bash
"$PYTHON" -B -m unittest -v test_direction_materials.DirectionMaterialsFreshnessTests.test_t4_answer_update_requires_a_stage4_refreeze 2>&1 | tee "$RUN/t4.out"
```

3. 判定与记录：逐项记录通过、业务失败、无法判断、未执行，并记下 `Ran N tests` 的数量；`save-entry-present.txt` 为 `False` 时 T2–T6 记未执行（模块内以 `skipTest` 表达同一结论），不得记通过。日志与原始产物只留在 `$RUN`，仓库只提交脱敏摘要。

4. 夹具构成（全部合成，已在预检中确认可生成）：单教授 `試験 教授`、方向 `DIR00001`/`DIR00002`，各 3 个候选、已选 idea；Stage-2/3 事实来自同仓 `BaseEnv` 的既有夹具，联系方式证据与核验缓存来自 `_stage5_issue59_test_support.py` 的既有写入器；模板来自 `stage5_templates()`。素材回答为固定合成日文，`question` 固定一句。模型输出是测试输入：刷新后重新读取 `stage5-plan` 的素材字段，再构造并提交本轮合成结果及草稿，不复用上一轮结果；不在测试中构造旧结果指纹。

5. 兼容输入（T5）只准备旧格式夹具，且必须同时还原**旧字段结构和旧版 `source_hash`**：取本轮 Stage-4 邮件包，删掉 `direction_material*` 字段与 `direction_material:<dir>:<id>` 来源 ID，再按功能加入前的摘要规则重算每条 email 的 `source_hash`，写回临时目录。旧版规则是 `main` `b67dd3c` 的 `EMAIL_SOURCE_HASH_FIELDS`（`email_id`、`direction_ids`、`directions`、`idea`、`papers`、`gaps`、`red_lines`、`allowed_sources`、`contact_evidence`、`cross_direction`）按 `json.dumps(..., ensure_ascii=False, sort_keys=True)` 取 SHA-256，与 runner 的 `sha256_obj` 编码一致；测试模块用 `legacy_source_hash()` 计算、`legacy_pack()` 组装，并在用例中断言该行的 hash 等于旧规则结果。只删字段而保留新规则算出的 hash 不算旧包，因为功能加入前的 producer 不会写出这种组合。不迁移历史真实包，也不新增旧版本全量迁移测试。

## 2.1 准备与预检记录（2026-10-27）

- 准备时 PR head：`37dc2b92a2145ad8dfcd4edd5aa9ca6692e60934`（仅计划，无产品实现）。
- 交付资产：
  - `.apm/skills/professor-contact/tests/test_direction_materials.py`：T2–T6 共 8 项，复用 `test_contact_state.py` 的 `BaseEnv`/`run_cli`、`_stage5_issue59_test_support.py` 的证据与核验写入器、`_stage4_handoff_test_support.py` 的行读取器；不新增运行平台。
  - `plan/test-grouping/shards.json`：模块登记到 shard3，stage 记为 `mixed:stage4+stage5`，`seconds` 记实测 22.7s（同一跳过路径测两次：20.4s／25.0s），`tests` 记 8，`signals` 按文档规则记 stage3 3、stage4 3、stage5 6（CLI 子命令字符串权重 3）；分片与全库合计按清单逐项求和（发布前已并入 main 的 PR145 模块一并计入）后为 86 个模块、1149 项用例、468.7s（三个原先缺 `tests` 字段的模块已按其 `unittest` 收集数补齐 8／8／8）；各分片的 `stages` 也改为按 `stage` 字段逐模块计数，使 README 的“模块数”与“阶段构成”两列一致。`python3 scripts/check_test_shards.py` 返回 `OK: 85 test modules across 4 shards, each with a stage`。
  - `plan/test-grouping/README.md`：按清单重新生成分片统计与逐模块表（85 行），并注明基线 `6e624e0` 的 1025 项／416.0s 实测未随新模块重算。
- 有限预检（临时目录 `/tmp/pr149-prep-20261027`，未执行必测用例的断言）：
  - 解释器可用（Python 3.14.7）；模块 `py_compile` 通过，`unittest` 收集到 8 项。
  - 既有夹具可生成两方向 Stage-4 交接：`stage3-finalize` 两方向均 `ok`，状态方向为 `DIR00001`/`DIR00002`；`stage4-finalize` `ok`，邮件包两条 email 各带 `allowed_sources`、`source_hash`、1 个可锚 gap；`stage5-plan` `ok`。
  - 无操作重编译两次，两条 email 的 `source_hash` 均不变（T4“无关方向不改变指纹”的前提成立）。
  - 取消选择后再次选择：`stage4-finalize` 均为 `ok`，取消后邮件包只剩 `DIR00002`，重选后两条恢复（T2 复选序列的前提成立）。
  - 预检同时观察到两个当前事实，供实现参考，不是正式结论：`stage5-finalize` 的邮件文件名是带方向与哈希后缀的 `套磁邮件_<方向>_<想法>_<hash>.md`，不是固定名；`validate_email_raw` 对未列入 `allowed_sources` 的来源返回 `source_map <句>: source <id> not in allowed_sources`。
  - 当前 runner 没有 `direction-materials-save` 子命令（符合实现前状态）；以未实现入口运行模块，8 项全部 `skipped`（`OK (skipped=8)`），记为未执行。
  - 按 §2 第 1 步的探测脚本实跑，`save-entry-present.txt` 输出 `False`，与上一条一致。
  - TP1.5 追加预检（`/tmp/pr149-prep-20261027/probe_legacy.py`，只检查夹具形状，不执行 T5 断言）：`legacy_pack()` 产出的行不含 `direction_materials`、不含 `direction_material:` 来源 ID，其 `source_hash` 等于按 `b67dd3c` 旧规则重算的结果，且与“把素材字段计入摘要”的新规则结果不同；把该旧包写回后 `stage5-plan` 返回 `ok`，`model_input` 不含 `direction_materials`。
- 未完成：第二关（本 recipe 的独立审核）、第三关（正式结果）；产品实现由实现负责人完成。下一负责人：独立 reviewer 确认第二关，再由本地执行工程师按本 recipe 运行。

## 3. 结果复用与范围控制

- 已合并 [PR148 TP1](../contact-email-natural/test-plan.md) 记录旧三部分规则/旧四项拒绝、模板与用户选择保护及既有结果。它不证明本次新素材功能；若相关实现未改，可由reviewer确认适用部分复用，不因为文档SHA变化重跑53项或全仓回归。
- 新素材冻结、source_map 和邮件输入 `source_hash` 的变化直接影响 T3–T5，必须得到针对新行为的有效证据；旧结果不能代替。相同目标不重复安排单元、集成及真实模型的同义测试。
- 仓库CI按既有配置自动触发可记录，不手动扩大本计划为全仓测试或修改CI分组设计。不因测试数、文件数新增门槛。
- 不要求安装重验、真实模型文风评分、完整套磁业务、来源过程/执行身份认证、跨教授自动匹配或并发压力矩阵。发现清单外问题报告事实与影响，不擅自扩大。

## 4. 失败、重试与关口

正式测试失败保留该次输出：明确产品偏离交实现负责人；recipe/环境错误记无法判断并停受影响项；未实现/没运行记未执行。按修订影响只重做受影响项，未受影响结果可复用。
本范围无外部服务采样，不安排自动重试。命令/环境失效时停止，确认原因并补齐步骤后再一次执行受影响项；业务失败不得通过换输入、放宽断言或重复采样求通过，原失败不得覆盖。
Gate1/设计由独立审核记录给结论；Gate2待独立 reviewer 审核本 recipe 的可执行性与范围；Gate3待有效结果。产品实施与正式执行均非本 PR 交付，本轮不声明可合并或已完成产品。

## 修订记录

TP1.5（2026-10-28，按第二关审核意见）：T5 的旧包夹具改为同时还原旧字段结构和旧版 `source_hash`——按 `b67dd3c` 的 `EMAIL_SOURCE_HASH_FIELDS` 重算，并删除 `direction_material:` 来源 ID；recipe 第 5 项同步写明规则与断言。只改 T5 测试数据与 recipe，未改必测目标、其它用例或产品需求；第二关仅需定向复核 T5。

TP1.4（2026-10-28，验收决定人主动精简）：随 EP1.2 将 T4 的旧模型结果指纹拒绝预期改为“更新回答→Stage4重冻→Stage5读取新素材→本轮重新生成结果、草稿并完成邮件”；删除模型结果素材指纹字段及对它的断言，同步修正 T3/T5 夹具。仍为 T1–T6、8 项测试方法；T1 的既有静态阅读覆盖生成器刷新后重新规划的约定，未增加真实模型运行。受影响的 T4 设计及 recipe 待复核；Gate3 未执行。

TP1.3（2026-10-28）：修正 §2 命令的起始目录与执行顺序；T6 删除跨教授 `material_id` 全局不同的断言，以及基于该假设的跨教授拒绝步骤，改为检查同名方向在两个教授目录各自保存且互不改写。必测 T1–T6 与 8 项测试方法不变；沿用已通过的第一关口，第二关口待复审，第三关口未执行。

TP1.2（本地测试工程师，2026-10-27）：按 §2 补齐可执行 recipe（受测入口、素材文件与来源 ID、冻结字段、保存入口标志与输出、解释器、隔离目录、命令、逐项目标映射、夹具构成），新增 T2–T6 的 8 项 producer 测试，并把模块连同 `seconds`/`tests`/`signals` 登记进 shard3、按清单重新生成 `plan/test-grouping/README.md` 的表。必测清单 T1–T6 与检查入口未改，没有新增测试目标或样本矩阵；产品实现与正式结果仍待完成。

TP1.2 复审修正（同一提交内）：按独立实现符合性审核 F1–F3 补齐分片清单的规模与信号字段并重生成 README；F5 把 T3 的来源断言从“素材 ID 出现在正文”收紧为“① 行来源列不等于裸机器 ID”；F6 的越界目录同时覆盖 program_root 之外与 `教授研究` 之外两种；F7 更正模块 docstring 的计划版本。第二轮复审 N1–N3 又修：README 补充 `mixed:` 标签与“仅夹具阶段不计入标签”的规则说明；`shards.json` 的 `stages` 改为按 `stage` 逐模块计数并补齐三个模块的 `tests`，`totals.tests` 由 1116 修正为 1140；README 写明用例数的求和口径。必测目标与样本数量不变。

TP1.2 发布前基线合并：main 已合并 PR145（Stage 2 来源解释窄修复入口），本分支合并 `origin/main` 解决 `plan/test-grouping/shards.json` 冲突，把 `test_stage2_source_evidence_repair`（9 项，stage2）登记进 shard4 并重生成 README；本次仅合并与分片登记，不改变本计划的 T1–T6、recipe 或测试代码。

TP1.1（历史版本）：当时加入的“Stage4已重冻但模型结果仍旧”的拒绝预期已由 TP1.4 取消；T4 改为核对更新后正常使用新结果。其余目标和Gate2/Gate3待办不变。


基线发布前更新至b67dd3c（PR146）：本功能与T1–T6目标/方法不变，Stage2/3追加轮次不纳入本计划；不因基线指针变化新增测试或重跑。
