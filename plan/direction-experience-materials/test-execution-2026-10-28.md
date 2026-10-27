# 方向真实素材：测试执行记录（2026-10-28）

- 执行计划：[execution-plan.md](execution-plan.md) EP1.2（Proposed review status: pending；[review.md](review.md) 的 P1–P4 PASS / APPROVED 对应 EP1.1，EP1.2 的语义修订仍待定向复核，本记录不把旧版批准复制给新版）。
- 测试计划：[test-plan.md](test-plan.md) TP1.5。必测清单 T1–T6 与 8 项测试方法未改；本轮按 §2 的精确 recipe 运行。TP1.5 的 Gate2 定向复核与 Gate3 结论属于独立 reviewer，本记录只提供实际命令、版本和逐项结果。
- 被测版本：`1a6011384b359b180a235b1174b6cdc6c049b6b3`（`feat(stage4, stage5): add direction-scoped experience materials`）。测试资产来自 PR head `3c6879e`；实现提交未改 TP1 的 8 个测试方法、selector、输入或预期结果。唯一的既有测试改动是 `test_stage3_direction_groups.py` 的 `source_hash` 辅助函数补上 EP1.2 新增的 `direction_materials` 字段，与 TP1 的旧包夹具（`legacy_source_hash()` 固定旧字段元组）互不影响。
- 实现范围：教授本地 `方向素材.json`（schema 1）与 `direction-materials-save`；Stage-4 冻结 `direction_materials[]`、`direction_material:<direction_id>:<material_id>` 来源与 `source_hash`；Stage-5 `model_input.direction_materials`、素材切片 freshness（`needs_refresh` / `direction_materials_changed`）和 md 来源表渲染；selection / generator / validator / SKILL / workflow-reference 的合同同步。
- 环境：macOS arm64；解释器 `/nix/store/0kcws5blwbdyxqxjd1w8hjipz61xny3k-python3-3.14.7/bin/python3`（Python 3.14.7）；工作树 `/Users/rekidunois/code/skill-repos-dev/worktree/professor-contact-pr149-execution-20261028`。
- 运行目录：`/tmp/contact-direction-materials.iMt6hj`；`TMPDIR=/tmp/contact-direction-materials.iMt6hj/tmp`，所有合成教授、素材、邮件与状态只落在这里，仓库内没有测试写入。`python-version.txt`、`tested-commit.txt`、`save-entry-present.txt`、`direction-materials.out` 保存本次正式输出。
- 实现前基线（同一测试模块、同一解释器，`pr149-test-preparation-20261027` 工作树在 `3c6879e`）：`save-entry-present.txt` 为 `False`，模块 `OK (skipped=8)`，据此 8 项记为未执行；该次输出不参与本轮结论。

## 结果总览

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 补问只针对缺少的真实方向素材 | 未执行（本角色不执行静态阅读） | 合同位置见下节，待独立 reviewer 按 TP1.5 静态核对并记录位置 |
| T2 正常保存与同方向复用 | 通过（2 项） | `direction-materials.out`：`test_t2_saved_answer_is_frozen_for_the_selected_direction_only`、`test_t2_selection_changes_do_not_delete_saved_materials` OK |
| T3 精确来源贯通与非法引用拒绝 | 通过（2 项） | `test_t3_frozen_material_reference_is_accepted_and_rendered`、`test_t3_unfrozen_material_cannot_be_cited` OK |
| T4 更新素材后重冻、重新生成且只刷新相关邮件 | 通过（1 项） | `test_t4_answer_update_requires_a_stage4_refreeze` OK |
| T5 新旧包兼容与素材被移走 | 通过（2 项） | `test_t5_pack_without_materials_keeps_old_behavior`、`test_t5_removed_material_is_a_slice_change` OK |
| T6 保存入口防错归属/覆盖 | 通过（1 项） | `test_t6_save_rejects_foreign_binding_and_stale_digest` OK |
| 全部 8 项 | 通过 | `Ran 8 tests in 31.283s`，`OK`，退出码 0 |

## 执行命令与结果

按 TP1.5 §2 从受测 checkout 仓库根目录依次运行：

1. 建立运行目录、设置 `TMPDIR`、记录解释器与受测提交，并探测正式保存入口：

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

实际输出：`Python 3.14.7`、`1a6011384b359b180a235b1174b6cdc6c049b6b3`、`True`。

2. 运行全部 8 项：

```bash
"$PYTHON" -B -m unittest -v test_direction_materials 2>&1 | tee "$RUN/direction-materials.out"
```

实际输出：`Ran 8 tests in 31.283s`、`OK`，退出码 0。按 TP1.5 §2 第 3 步记录：`save-entry-present.txt` 为 `True`，8 项均有实际运行结果，不记未执行。

## 逐项观察

- T2：回答按原字节保存在独立 `方向素材.json`，未进入 profile 或 `套磁候选状态.json`；同一方向换 idea 后继续冻结同一 `material_id`，取消选择再选不删除素材；方向 B 的 `direction_materials` 为 `[]` 且不带方向 A 的来源 ID。
- T3：`stage5-plan` 的 `model_input.direction_materials` 含方向 A 的原回答；① 引用冻结来源时 finalize `ok`，md 来源表的 ① 行显示可读来源而不是裸机器 ID；其他方向或不存在的素材 ID 被 `allowed_sources` 拒绝且已提交邮件字节不变；③ 仍只能用 `gap:`，用素材代替 gap 被拒绝。
- T4：更新回答后旧包在 `stage5-plan` 与 `stage5-finalize` 均返回 `needs_refresh`，邮件、纯文本与状态字节不变；经 Stage-4 重冻后 `source_hash` 改变，`model_input.direction_materials` 与邮件包都含新回答，重新生成的结果与草稿可完成新邮件；只改未选方向 B 时 A 的 `source_hash` 不变。
- T5：旧包按旧字段元组重算 `source_hash`，无素材字段时 plan/finalize 正常；该方向新增素材后旧包 `needs_refresh` 且不覆盖已有邮件；Stage-4 重冻后可继续生成。把素材文件移走同样识别为切片变化。
- T6：方向不在该教授正式范围、教授目录越出 `教授研究`（程序根同级与程序根内部两种）均拒绝且不生成素材文件；陈旧摘要拒绝且原字节不变；正确摘要更新同一条目而不重复；损坏文件不被当作空库覆盖；同名方向在另一教授目录各自保存、互不改写。

## T1 合同位置（供独立 reviewer 静态核对）

本角色不执行 T1 的人工静态阅读，也未把阅读结论写成自动断言。实现后的合同位置如下，供独立 reviewer 按 TP1.5 T1 的观察点逐项核对：

- `.apm/agents/professor-contact-selection.agent.md`：Input 的 `materials`；Step 2.5 的缺素材补问、已有回答不重复、Codex `needs_input` + `pending_materials`、用户回答后 fresh 委派、`direction-materials-save` 参数与独立保存语义；Return value 的 `pending_materials[]` 与 `needs_input` 行。
- `.apm/skills/professor-contact/SKILL.md`：Stage 4 的「方向真实素材（EP1.2）」caller contract；Input contract 的 `materials` 行；持久化产物 `<教授名>/方向素材.json`。
- `.apm/agents/professor-contact-email-generator.agent.md`：「Direction-scoped experience materials (EP1.2)」的冻结切片、来源 ID、`needs_refresh` 回 Stage 4 和重新 plan/生成/草稿规则；Execution summary 首步与末尾的刷新说明。
- `.apm/agents/professor-contact-email-validator.agent.md`：规则 1 的 `direction_material:` 来源、规则 13 的素材不得改写/升级、规则 14 的跟进检查；Step 1 读取 `direction_materials[]`。
- `.apm/skills/professor-contact/docs/workflow-reference.md` §8 的方向素材保存/冻结说明与 §9 的素材切片 freshness 说明。

## 既有回归（非必测，实现自检）

以下结果不替代 T1–T6，也不扩大测试范围，只用于确认本次实现没有破坏直接受影响的既有合同：

- 在最终代码 `1a60113` 上复跑：`test_contact_state` `Ran 90 tests in 241.973s`，`OK`；全 shard3（`check_test_shards.py --print shard3`）`Ran 288 tests in 487.072s`，`OK`；全 shard2（`--print shard2`）退出码 0（同一模块集此前一次完整输出为 `Ran 227 tests in 273.865s`，`OK`）。
- 推送后 CI run `40574397594`（head `50c33ad`，相对 `1a60113` 只多本记录）：`shards (shard1)`–`shards (shard4)` 与聚合 `test` 全部 pass。CI 不是 TP1 的必测项，只作既有回归复核。
- 文档补充后重跑 selection/stage4/stage5 合同、部署元数据与 routing 合同：`Ran 121 tests in 12.969s`，`OK`。

## 未完成项与下一负责人

- Gate2：TP1.5 的 T5 定向复核与 recipe 范围审核仍待独立 reviewer；本记录不声称 Gate2 通过。
- Gate3：T2–T6 已给出当前版本的实际结果；T1 未执行，需独立 reviewer 完成静态阅读后才能形成必测清单的完整结论。本记录不自授 Gate3 或合并许可。
- 实现符合性审核：待独立 `implementation_reviewer` 核对；其结论只覆盖实现符合性，不是计划/测试关口或合并批准。
- 下一负责人：独立 reviewer（T1 静态阅读、Gate2 定向复核、采用本记录给出 Gate3）；随后由 merge reviewer 按 `Merge Reviewer Rule.md` 处理。
