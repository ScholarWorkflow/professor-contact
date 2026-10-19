# Stage 2 划分第七批：渲染与校验层（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-render/implementation-plan.md` 第 3 版。
- 测试计划：`plan/stage2-render/test-plan.md` 第 3 版。
- 被测提交：`ebf2763`（`refactor(stage2): move the render layer into a helper module`，父提交 `980aa18` 为计划文档提交，其父为分支链上一位 `5972905`）；当前分支 head `800e297`，它只把 `_stage2_finalize.build(...)` 调用里一行孤立 `,` 折进上一行，runner 的 AST 与 `ebf2763` 相同。
- 对照基准：分支链上一位 `refactor-stage2-context`（#113）的 head `5972905b1aa420f5aebdbd9a06221958fe64a726`，runner 7630 行。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage7/`（`base/` 是父提交导出的 scripts，`blocks/blk0.sh`–`blk5.sh` 是从测试计划第 3 版原文抽出的命令块）。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与两个工厂契约 | 通过 | 7 条 `T0 ... OK`：渲染 `build()` 16 个 keyword-only 参数、12 个成员；finalize `build()` 40 个参数、7 个成员；runner 12 个别名且两个标题 helper 不再指向 finalize；16 个实参同名同集合、别名在调用之后；两个加载块都用 `Path(__file__).with_name(...)`；渲染模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；`T0 CHECKS PASS`；`py_compile` 与 `--help` 退出码 0 |
| T1–T3 结构／AST／接口 | 通过 | 58 条 `OK`（T0 3、T1 21、T2 13、T3 21）、`ALL CHECKS PASS`、退出码 0；`--help` 与父提交逐字节相同（`diff -u` 无输出，`/tmp/pc-stage7/compare.log`） |
| T2 标题 helper 跨模块 | 通过 | 2 条 `T0 ... OK`：两个 helper 在 `_stage2_finalize.py` 中消失、在 `_stage2_render.py` 中出现且 AST 与基线相同；`base - head == {两个 helper}`；finalize 其余 13 个 helper AST 不变（`/tmp/pc-stage7/relocate.log`） |
| T4 渲染／校验层行为 | 通过 | 7 个方法：`Ran 7 tests in 8.372s`、`OK`，无失败、无跳过（`/tmp/pc-stage7/t4.log`） |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests in 1.005s`、`OK`（`/tmp/pc-stage7/t5.log`） |
| 失败注入 | 不适用 | 本批只搬移定义并把两个标题 helper 换到渲染模块，不改事务／回滚／写入顺序／错误通道 |
| 失败对照（父提交，未触发） | 通过 | 9 个方法（T4 7 + T5 2）在 `5972905` 上：`Ran 9 tests in 9.800s`、`OK`，退出码 0（`/tmp/pc-stage7/baseline.log`） |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号；不作为通过条件 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，7085 行，sha256 `4c0ff3f910d8605dfd264ab7e7506483e25de3df45d32de6776e77f5cbe59974`（实现提交后清掉了 finalize 调用里一行孤立 `,`，语法与行为不变，A/B 仍为 58 条 OK、`--help` 仍逐字节相同）。
- 新模块：`.apm/skills/professor-contact/scripts/_stage2_render.py`，667 行，sha256 `c96217c55ea897bf24068f263dd34eb41085f762546190aef72efb9196ca52be`（10 个搬移定义 + 两个移入的标题 helper，`build()` 16 参数、12 成员）。
- 改动的已合并模块：`.apm/skills/professor-contact/scripts/_stage2_finalize.py`，885 行，sha256 `243d71638a36985df4f7a232b470e23446a6d51697d4fac1b6563872661f4ddc`；相对父提交 `+4 −37`（删 33 行 helper + 2 行成员表，加 2 个参数与 2 行签名）。
- 代码 diff（`5972905` → 工作树）：runner `+46 −591`（`git diff --numstat`），其中删除侧是 10 个定义 571 行加删除后收敛掉的空行，新增侧是加载块 12 行、绑定块与 12 个别名、finalize 调用新增 3 行。
- `git diff --ignore-blank-lines -U0` 的 runner hunk 正好 4 个：`@@ -231,0 +232,12 @@`（渲染加载块）、`@@ -1461,589 +1473,33 @@`（10 个定义删除与绑定块）、`@@ -2093 +1549,2 @@`（finalize 调用补 2 个实参）、`@@ -2102,2 +1559,0 @@`（旧的两行标题别名删除）；`_stage2_finalize.py` 另有 3 个 hunk（33 行删除、签名加 2 个参数、成员表删 2 行）。
- 无关空行保持原样：基线里 5 处“≥4 个连续空行”在改动后仍是 5 处、长度相同（只随删除整体前移）。

## 说明与偏差

- **绑定环与解法**：父提交里 `render_analysis_md`（1901）必须在 `_stage2_finalize.build(...)`（2054）之前提供，但它运行期调用的 `stage2_require_later_paper_titles` 到 2103 才有别名。本批把 `stage2_trusted_paper_title`（11 行）与 `stage2_require_later_paper_titles`（22 行）从 `_stage2_finalize.py` 移进渲染模块，环消失：渲染模块在 1461 绑定，finalize 在 2054 通过新参数拿到这两个名字，validation 在 6700 仍从 runner 别名取。两个 helper 的函数体未改（AST 与基线相同）。
- **注入名 16 个**：实施前演练第一次只写了 15 个，漏掉 `Stage2PackRefineContext`，`stage2-finalize` 直接 `NameError`；补上后 T4／T5 全绿。该教训已写进执行计划的风险条目。
- **本批编辑了已合并模块**：`_stage2_finalize.py` 的工厂签名从 38 变 40、成员从 9 变 7；模块内 Load 点共 5 处，除同批搬走的那一处外都由新参数提供。这是本批唯一越出“只搬 runner 定义”的动作，已在执行计划的“取舍”里说明为什么不用晚绑定或转发函数。
- **probe 清扫**：演练产物落到工作树后清掉了两处自造痕迹（删除定义后遗留的 21 行空行收敛为 2 行、finalize 调用里多余的孤立 `,` 行）；基线自带的空行块未动。
- 环境与工具：对比脚本 `compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）、提取器 `extract_batch_v2.py`（134 行，sha256 `336c58e1937e7e735b1d1678a39630618ae5c6917ecc6be29b93a4b4e6f14b5b`）；两个标题 helper 的跨模块核对是测试计划第 2 步第二段的内联只读脚本，不新增工具。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage7/blocks/blk0.sh`（7 条 `T0 ... OK`）；更早一次同类成功运行留在 `/tmp/pc-stage7/ab.log`（58 条 `OK`）。
- T1–T3：`/tmp/pc-stage7/blocks/blk1.sh`（`diff` 无输出 + 58 条 `OK`）。
- 标题 helper 跨模块：`/tmp/pc-stage7/blocks/blk2.sh`（2 条 `T0 ... OK`）。
- T4：`/tmp/pc-stage7/blocks/blk3.sh`（`Ran 7 tests`、`OK`）。
- T5：`/tmp/pc-stage7/blocks/blk4.sh`（`Ran 2 tests`、`OK`）。
- 失败对照（未触发）：`/tmp/pc-stage7/blocks/blk5.sh`（9 个方法、`OK`）。
