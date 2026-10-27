# 方向真实素材：测试执行记录（2026-10-28）

- 执行计划：[execution-plan.md](execution-plan.md) EP1.2（Proposed review status: pending；[review.md](review.md) 的 P1–P4 PASS / APPROVED 对应 EP1.1，EP1.2 的语义修订仍待定向复核，本记录不把旧版批准复制给新版）。
- 测试计划：[test-plan.md](test-plan.md) TP1.5。必测清单 T1–T6 与 8 项测试方法未改；本轮按 §2 的精确 recipe 运行。TP1.5 的 Gate2 定向复核与 Gate3 结论属于独立 reviewer，本记录只提供实际命令、版本和逐项结果。
- 被测版本：首轮 `1a6011384b359b180a235b1174b6cdc6c049b6b3`（`feat(stage4, stage5): add direction-scoped experience materials`），8/8 通过；实现符合性审核修正 `1084a409ae52d0098f6f3b93872df8251d700302`（`fix: close direction-material review gaps`）后在同一 recipe 上复跑 8/8 通过（`RUN=/tmp/contact-direction-materials.PE7cvb`）。测试资产来自 PR head `3c6879e`；实现提交未改 TP1 的 8 个测试方法、selector、输入或预期结果。唯一的既有测试改动是 `test_stage3_direction_groups.py` 的 `source_hash` 辅助函数补上 EP1.2 新增的 `direction_materials` 字段，与 TP1 的旧包夹具（`legacy_source_hash()` 固定旧字段元组）互不影响。
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
| 全部 8 项 | 通过 | 首轮 `1a60113`：`Ran 8 tests in 31.283s`，`OK`，退出码 0；修正 `1084a40` 后复跑：`Ran 8 tests in 22.456s`，`OK`，退出码 0 |

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

## 实现符合性审核与复验（2026-10-28）

独立 `implementation_reviewer` 首审结论为“部分完成”，发现 4 项合同/错误通路问题；本角色修正后提交 `1084a40`：

- F1（selection 失败分支）：Step 2.5.5 与 Hard rules 区分可重读后重试的 `materials_digest_changed`/`materials_already_exists`，与必须停止该教授、零 Stage-4 写入的 `invalid_direction_materials`/`unknown_direction`/`invalid_professor_dir`/`invalid_params`；Errors 增加该教授 input-error 行的终止出口。
- F2（needs_input 枚举与聚合）：Return 的 `results[].status` 示例补 `needs_input`；明确“有其他成功 → partial，全部停在真实用户输入 → needs_input，无成功且无待输入 → error”。
- F3（保存入口摘要/异常）：`--expected-sha256` 改为对原始字节取摘要，`OSError` 转 `invalid_direction_materials` 结构化失败；T6 在 `1084a40` 上复跑通过。另用非 UTF-8 字节 `b"\xff\xfe{not json"` + 正确旧摘要做一次定向自检：退出码 1、`status=error`、`reason_code=invalid_direction_materials`、stderr 无 traceback、原字节不变。
- F4（validator 冒充）：规则 13 与 Step 2 要求使用 `direction_materials[].answer` 的经历必须标该条 `direction_material:` 来源；标成 `profile.interest`/`user_note`/`paper:`/`gap:` 承载同一经历 → blocking（无法判断时 minor）。

同批澄清：`answer` 是用户数据而不是指令/授权；已有 profile/补充足以写出有事实依据的接触描述时不再重复问。修正后 TP1 8 项复跑通过；selection/validator/generator 与 Stage5 合同批 `Ran 148 tests in 27.449s`，`OK`。

定向复核（基线 `c255904`）确认 F3/F4 关闭；F1 原缺陷关闭，但发现三项残余：F1-R1（Step 2.5.5 仍写“或调用级 error”，与 Errors 的教授行终止出口矛盾；该句已在 `a1ac428` 删除）、F1-R2（`--expected-sha256` 遇到文件已删除仍返回 `materials_digest_changed`，合同却要求重读摘要）、F2-R1（无成功 + 待输入 + 失败的混合批次没有一致聚合规则）。残余修正提交 `181b356`：

- F1-R1：合同只保留 Errors 的教授 input-error 行出口；
- F1-R2：`materials_digest_changed` 后重读发现文件不存在时停止该教授保存并报告，不按同一 `material_id` 重新追加；
- F2-R1：selection Step 2.5.4、Return 与 SKILL Stage 4 统一为“任一成功 → partial；无成功且存在失败/错误 → error（needs_input 行保留展示）；无成功且全部停在真实用户输入 → needs_input”。

残余修正只改合同文字（selection/SKILL），未改产品代码、TP1 测试方法或输入，`1084a40` 的 T2–T6 结果继续适用；合同批在修正后 `Ran 135 tests in 9.842s`，`OK`。

最终定向复核（基线 `112a22d`）结论：**完整（仅实现符合性）**。F1-R1、F1-R2、F2-R1 关闭，F3/F4 的先前关闭不受影响；未发现新的直接行为偏差，只有三条不影响结论的可选措辞清理，未因此改动测试或产品。该结论不是 Gate2/Gate3 或合并批准。

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
- 推送后 CI run `40574397594`（head `50c33ad`）、`40577168299`（head `c255904`）与 `40578210640`（head `112a22d`）：三次的 `shards (shard1)`–`shards (shard4)` 与聚合 `test` 全部 pass。CI 不是 TP1 的必测项，只作既有回归复核。
- 文档补充后重跑 selection/stage4/stage5 合同、部署元数据与 routing 合同：`Ran 121 tests in 12.969s`，`OK`。
- 复核修正 `1084a40` 后重跑同类合同批（含 `test_stage5_immutable`）：`Ran 148 tests in 27.449s`，`OK`。

## 未完成项与下一负责人

- Gate2：TP1.5 的 T5 定向复核与 recipe 范围审核仍待独立 reviewer；本记录不声称 Gate2 通过。
- Gate3：T2–T6 已给出当前版本的实际结果；T1 未执行，需独立 reviewer 完成静态阅读后才能形成必测清单的完整结论。本记录不自授 Gate3 或合并许可。
- 实现符合性审核：首审“部分完成”（F1–F4，修正 `1084a40`）；定向复核确认 F3/F4 关闭、F1/F2 有残余（F1-R1/F1-R2/F2-R1），已在 `a1ac428`/`181b356` 处理；最终定向复核结论“完整（仅实现符合性）”。该结论不是计划/测试关口或合并批准。
- 下一负责人：独立 reviewer（T1 静态阅读、Gate2 定向复核、采用本记录给出 Gate3）；随后由 merge reviewer 按 `Merge Reviewer Rule.md` 处理。
