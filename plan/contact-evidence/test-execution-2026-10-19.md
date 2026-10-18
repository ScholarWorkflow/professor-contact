# 边界三：联系证据上游层搬移 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 2 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 3 版（`Plan conclusion: APPROVED`）。
- 对照基准：`2117fc6a1607a22aa9e723002b4a78625733b7b1`。
- 被测提交：`c8c7208`（实现提交；其后如仅改文档，产品与测试字节不变）。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-bnd3-check/`。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | `base2.json` 与 `head2.json` 逐字段相同：显式注入存在文件返回该路径、注入缺失文件返回 `None`（失败关闭）、注入空白串与不注入都退回环境解析且两侧结果相同（同构目录下均为 `None`） |
| T2 | 通过 | 同一对比（八种场景）：fresh → `check`；stale → `check, rebuild, check`；per-professor unavailable → `check`（不重建）；无条目 unavailable → `check, rebuild, check`；重建失败 → `check, rebuild` 且 `rebuild_ran: False`；check 非零退出／非 JSON／`result` 非法值 → `check` 且 `checker_error: script_failed`、不重建。八种场景返回字典的 5 个键与内容相同，stub 调用日志序列一致 |
| T3 | 通过 | 同一对比：合法 artifact、kind 不符、schema 不符、非对象、坏 JSON、缺失六种输入的 `(artifact, error)` 相同；runner 侧 `load_contact_evidence` 签名仍是 `(program_root)` |
| T4 | 通过 | 同一对比：六种教授名形态（全角空格、首尾空格、stale/legacy/invalid/不存在）与七种状态（None/fresh/stale/legacy/invalid/unavailable/空对象）结果相同；runner 侧 `professor_source_state` 签名仍是 `(report, professor)` |
| T5 | 通过 | `Ran 5 tests in 9.758s`，`OK`，退出码 0 |
| 既有仓库检查 | 待补 | 推送到 PR 后引用仓库 CI 运行编号、所跑 head 与 `test` 检查状态（不属于本批必测项） |

## 执行方法与命令

1. 取基准副本，并把改动版复制到**同构目录**：

   ```sh
   RUN=$(mktemp -d /tmp/pc-bnd3-XXXXXX)
   mkdir -p "$RUN/base" "$RUN/head"
   for name in contact_state _stage3_render _contact_io _stage3_handoff; do
     git show 2117fc6a...:.apm/skills/professor-contact/scripts/$name.py > "$RUN/base/$name.py"
   done
   cp .apm/skills/professor-contact/scripts/contact_state.py .apm/skills/professor-contact/scripts/_*.py "$RUN/head/"
   ```

   这一步是必须的：`upstream_check_script` 用 `Path(__file__).resolve().parents` 解析同级 skill 与兄弟 checkout；若基准留在 `/tmp`、改动版留在仓库目录，两侧解析结果天然不同。

2. T1–T4：同一驱动分别加载两侧 runner，输出归一化（工作目录替换为 `<WORK>`）后逐字段比较：

   ```sh
   set -e
   uv run --no-project "$RUN/evidence_probe.py" "$RUN/base/contact_state.py" "$RUN/base-work2" > "$RUN/base2.json"
   uv run --no-project "$RUN/evidence_probe.py" "$RUN/head/contact_state.py" "$RUN/head-work2" > "$RUN/head2.json"
   diff -u "$RUN/base2.json" "$RUN/head2.json"
   ```

3. T5：清单列出的 5 个入口（见测试计划第 3 步），`Ran 5 tests`、`OK`。

4. 搬移核对：基准的 `148-150`、`154-163`、`8373-8529` 三段反向套用 6 处文档化改动（3 处签名加注入参数、2 处 `load_contact_evidence` 内部调用、1 处 `professor_source_state` 内部调用）后，与新模块正文逐字节相同。

## 执行中修正的测试资产问题（保留记录）

- 首轮对照出现两处差异（`injected_blank` 与 `no_injection` 的解析结果），定位为**假差异**：基准 runner 是 `/tmp` 里的副本、改动版在仓库目录，`upstream_check_script` 基于 `__file__` 的解析在两种位置下必然不同。把两侧都复制到同构目录后重跑，逐字段相同。该做法已写进测试计划的准备步骤与说明。
- 以上属测试资产问题，不是产品缺陷；修正后整体重跑受影响编号。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果按运行编号与所跑 head 单独记录，按测试计划不属本批业务必测项。

## 结论与交接

- T1–T5 对被测提交取得有效通过结果；既有仓库检查待 PR 打开后补运行来源。
- 本记录之后如只改文档，未改产品与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批堆叠在边界二分支 `refactor/stage3-handoff`（PR #100）之上，合并顺序 #97（已合并）→ #98 → #99 → #100 → 本批。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
