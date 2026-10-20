# 校验链三函数划分：`_fingerprint_failure_kind`、`_verify_diagnostic_failure`、`verify_state`（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-21 负责人要求：把 `contact_state.py` 收敛为 CLI 分发与兼容入口，按批拆 PR，每批都要计划、测试与审核；原文见会话记录。同一系列见 PR #95–#127）。
- Plan revision: 第 4 版。
- Proposed review status: pending。
- Target repository revision: 工作分支 `refactor-verify-chain`，父提交 `58c71c02cd0b6d66aae4cda5b7cc815431a461e6`（第 20 批 head，基于 `972d4fd4…`；`origin/main` 的 PR #126 合并提交 `fb1e31d` 与 `972d4fd` 同树，HEAD 就是 `58c71c0`）；工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain`。
- 参考做法：`_stage4_commands.py`、`_candidate_validate.py`、`_email_core.py`、`_direction_inputs.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 验收条件 |
| --- | --- |
| R1 | `_fingerprint_failure_kind`、`_verify_diagnostic_failure`、`verify_state` 不再是 runner 顶层的 `FunctionDef`；三者定义在 `_verify_chain.py` 的 `build()` 内；runner 保留同名别名，且 `getattr(runner, name) is getattr(runner._verify_chain, name)`。别名顺序不作契约。 |
| R2 | 三个函数体与父提交的 AST 相等（比较时忽略 docstring）；94 行非空源码去掉行首缩进后逐行相同、空行位置允许因搬移变化，`verify_state` 内 12 行 Issue-#10 注释必须按顺序保留；`_fingerprint_failure_kind` 的 docstring 原文保留，另两个原本没有 docstring；运行时自由名字只来自模块导入（`datetime`、`timedelta`、`timezone`）、`build()` 内的两个兄弟函数与 6 个注入名，没有反向导入。 |
| R3 | 新模块只导入 `__future__`、`datetime`、`pathlib`、`types`、`typing`；不导入 runner，不改 `sys.path`，不写 `sys.modules`，不做动态导入，不另建失败通道。 |
| R4 | 加载块插在父提交 1200 行（`cmd_stage4_migrate_local` 与其后 2 行空行之后、`def _fingerprint_failure_kind` 之前）；绑定块插在父提交 1386 行之后（`render_fact_check_card` 与其后 2 行空行之后）；6 个注入名在父提交最晚于 1370 行（`current_source_fingerprints`）已赋值；唯一消费方是 `_stage5_commands.build`（父提交 1424 行，`verify_state=verify_state` 在 1454 行），不得提前到 `_stage5_email.build`。 |
| R5 | `build()` 恰好 6 个 keyword-only 参数，无位置参数、无默认值：`read_json_file`、`VERIFY_TTL_DAYS`、`VERIFY_TIMESTAMP_FORMAT`、`VERIFY_FILE`、`email_item_is_evidence_seeded`、`current_source_fingerprints`；6 个参数都被函数体使用，没有只收不用的占位。 |
| R6 | 顶层字面量常量仍为 67 个，名字集合与值都不变；`--help` 输出逐字节不变（3221 字节，sha256 `d622b7e69794bb81b04f456c642f82bc72eab7c9f1e197fb4c44a2ece7157c03`）；T4 的 3 个方法与 T5 的 1 个方法通过。 |
| R7 | diff 只包含预期的三类改动：删除 1200–1297 的 3 个定义（94 行源码 + 4 行空行）、插入加载块、插入绑定块与 3 个别名；没有其他语义改动。2 个 hunk（`-U0` 与默认上下文都是 2）与净变更 `+27 −98` 是通过条件，用来确认抽取模板按原样套用；runner 2014 行、模块 129 行只作观察值记录，不作通过条件。改动范围只有 `contact_state.py`（修改）、`_verify_chain.py`（新增）、`plan/verify-chain/`（新增）。 |

本批要求“不做格式重排”，所以 hunk 数与 `+27 −98` 是硬条件；如果确实要接受格式差异，那属于范围变更，要先改计划再执行，不能在执行时把它记成观察值。

## 范围：3 个定义共 94 行

| 定义 | 行区间（父提交） | 行数 |
| --- | --- | --- |
| `_fingerprint_failure_kind` | 1200–1214 | 15 |
| `_verify_diagnostic_failure` | 1217–1220 | 4 |
| `verify_state` | 1223–1297 | 75 |

删除区间为 1200–1297，共 98 行：94 行定义源码加 4 行空行（1215–1216、1221–1222）。94 行源码里包含 `verify_state` 的 12 行 Issue-#10 注释（1242–1246 的 linkage、1251–1257 的 conflict gate），这些注释必须随源码原样搬移；AST 不包含注释，所以 R2 另外要求源码文本核对。区间内没有需要保留的分隔语句；区间外不删任何行。

## 需要注入的 6 个名字

| 名字 | 父提交行 | 说明 |
| --- | --- | --- |
| `read_json_file` | 512 | runner 顶层别名，不是 `def` |
| `VERIFY_FILE` | 437 | 常量 `"_contact_verify.json"`，模块不复制字面量 |
| `VERIFY_TTL_DAYS` | 472 | 常量 `30` |
| `VERIFY_TIMESTAMP_FORMAT` | 473 | 常量 `"%Y-%m-%dT%H:%M:%SZ"` |
| `email_item_is_evidence_seeded` | 1369 | `_stage5_email` 的别名，6 个名字里较早赋值 |
| `current_source_fingerprints` | 1370 | 6 个名字里最晚赋值，绑定块必须在其后 |

## 实测自由名字

| 定义 | 运行时自由名字（`symtable`，去掉内建名） |
| --- | --- |
| `_fingerprint_failure_kind` | 无 |
| `_verify_diagnostic_failure` | 无 |
| `verify_state` | 模块导入 `datetime`、`timedelta`、`timezone`；兄弟函数 `_fingerprint_failure_kind`、`_verify_diagnostic_failure`；注入名 `read_json_file`、`VERIFY_FILE`、`VERIFY_TTL_DAYS`、`VERIFY_TIMESTAMP_FORMAT`、`email_item_is_evidence_seeded`、`current_source_fingerprints` |

模块带 `from __future__ import annotations`，`Path`、`Any` 只出现在注解字符串里，不参与运行时自由名字；AST 层面它们仍是 `Name` 节点，所以 AST 相等检查同样有效。

## 为什么这 3 个必须同批

- `verify_state` 在父提交 1272、1283、1292、1295 行共 4 次调用 `_verify_diagnostic_failure`，在 1285 行调用 `_fingerprint_failure_kind`。
- `_verify_diagnostic_failure` 与 `_fingerprint_failure_kind` 除了被 `verify_state` 调用之外，在 runner 内没有其他消费方；三者合起来是一个闭合的依赖组。
- 三者在父提交占据连续的 1200–1297 行，中间只有 4 行空行；拆成两批会留下只被模块使用的私有函数，或需要临时反向导出。
- 唯一的外部消费方是父提交 1424 行的 `_stage5_commands.build`；绑定点放在 1386 行之后即可同时满足 6 个依赖和消费顺序。

## 替代方案比较

| 方案 | 做法 | 取舍 | 结论 |
| --- | --- | --- | --- |
| A. 工厂闭包（本批） | `build(**deps)` 把 6 个注入对象绑进闭包，返回 `SimpleNamespace` | 与前 10 批一致；函数体只改缩进；不碰 `sys.path`、不反向导入；代价是依赖变成导入时的快照，`__module__`/`__qualname__` 变化 | 采用 |
| B. 加载后给模块赋属性 | 模块顶层留空名字，runner 执行 `module.read_json_file = read_json_file` 后再调用 | 同样不反向导入，但名字是可变模块状态，谁在何时赋值无法从签名看出；顺序错了要到调用时才报 `AttributeError` | 不采用 |
| C. 反向 `import contact_state` | 模块顶部 `from contact_state import ...` | 违反“模块不导入 runner、不依赖脚本目录在 `sys.path` 上”的既有约束，直接执行与按路径加载会得到两个模块对象 | 不采用 |
| D. 类或显式状态对象 | 把 6 个依赖收进一个对象，函数改成方法 | 要改每个函数的调用形式与函数体，超出“只搬移”的范围，A/B 也无法用 AST 相等核对 | 不采用 |

## 影响分析

| 项目 | 内容 |
| --- | --- |
| intended_change | 3 个定义从 runner 顶层移入 `_verify_chain.py` 的 `build()`；runner 保留 3 个同名别名与加载/绑定块 |
| preserved_behavior | 函数体、docstring、注释、签名、调用方与 `--help` 都不变；67 个顶层常量不变；`read_json_file`、`current_source_fingerprints` 等对象本身仍是 runner 自己的对象（别名 `is` 成立） |
| approved_behavior_change | 无业务行为变化。仅有三类可观察差异：`verify_state.__module__` 变为 `_verify_chain`、`__qualname__` 带 `build.<locals>`；`inspect.getsource` 读取的是模块文件；嵌套函数不能按引用 pickle（父提交的顶层函数可以）。三者都不在仓库的调用面上（见下行证据），本批把“不支持 pickle 这些函数”写成冻结的内部约定 |
| prohibited_side_effect | 不新增失败通道、不写 `sys.path`/`sys.modules`、不复制常量字面量、不改变 `_stage5_commands` 之外的消费方、不改 CLI 参数与帮助文本 |
| unresolved impact | 闭包捕获是“导入时快照”：如果有人在 runner 导入后重新赋值 `contact_state.read_json_file`、`current_source_fingerprints`、`email_item_is_evidence_seeded` 或 3 个 `VERIFY_*` 常量，三个函数不再看到新值。仓库内检索（`tests/`、`scripts/`）没有发现对这些名字的 `monkeypatch`、`patch(` 或重新赋值；若将来出现，属于本批冻结的内部约定被打破，需要新计划 |
| 证据检索 | 在 `tests/` 与 `scripts/` 检索这 6 个名字，只命中定义处、别名与调用处；测试通过 `helpers.raw_cli` 启动子进程，不修改 runner 命名空间 |
| Nix / 安装布局 | `nix/contact.nix` 的 `runtime` 用 `cp -R` 整树复制 `.apm/skills/professor-contact`，新模块随包进入安装，不需要改 `entryNames`；`_verify_chain` 缺失时加载块在导入期抛 `RuntimeError`，T5 用复制后的夹具覆盖同类布局 |

## 设计

- 新模块 `_verify_chain.py` 与 `contact_state.py` 同目录，只暴露 `build()`；`build()` 返回 `types.SimpleNamespace`，成员为 `_fingerprint_failure_kind`、`_verify_diagnostic_failure`、`verify_state`。
- 工厂用 keyword-only 参数把 runner 的函数对象与常量绑定进闭包；三个函数只改缩进，不改函数体与注释，因此不需要反向导入，也不产生第二条读取路径。
- 加载块 11 行：4 行注释、`_VERIFY_CHAIN_PATH = Path(__file__).with_name("_verify_chain.py")`、两行 `spec_from_file_location`、两行 `None` 检查并 `raise RuntimeError`、`module_from_spec`、`exec_module`；加载块沿用模板注释原文，只把首行改成 `# Verify-chain helper module: ...`。
- 绑定块 10 行：2 行注释、1 行 `_verify_chain = _verify_chain_module.build(`、6 行同名关键字实参、1 行 `)`；每个实参都是同名 `ast.Name`，顺序与签名一致。
- 绑定块后紧跟 3 行别名：`_fingerprint_failure_kind`、`_verify_diagnostic_failure`、`verify_state`，都指向 `_verify_chain` 的同名属性；别名顺序不作为契约。
- 模块 docstring 首行由抽取模板的 `Stage-2 helper module` 改为 `Verify-cache helper module`，改法见实施步骤第 2 步；模块共 129 行（观察值，非验收契约）。

## 实施步骤

0. 确认工作树、基线，并选择执行方式：
```sh
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
git rev-parse HEAD
git status --porcelain
grep -c '^def _fingerprint_failure_kind' .apm/skills/professor-contact/scripts/contact_state.py || true
```
预期：HEAD 等于 `58c71c02cd0b6d66aae4cda5b7cc815431a461e6`。当前工作树是“已应用改动”的核对起点（`M contact_state.py`、`?? _verify_chain.py`、`?? plan/verify-chain/`），且 runner 里已经没有 `def _fingerprint_failure_kind`（`grep -c` 输出 0）。因此本批有两条互斥路径：
   - **路径 B（本次实际执行，核对）**：跳过第 1–3 步，直接跑第 4–6 步与测试计划。
   - **路径 A（干净重跑，生成）**：`git worktree add /tmp/pc-b21-clean 58c71c02…` 建一个只用于抽取的干净工作树；`cp /tmp/pc-stage21/spec-b21-real.json /tmp/pc-stage21/spec-b21-clean.json`，把 `worktree` 改成 `/tmp/pc-b21-clean`、`out_dir` 改成 `/tmp/pc-stage21/clean-probe`；在那里跑第 1–3 步，随后把 `contact_state.py` 与 `_verify_chain.py` 复制回当前工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain`。第 4–6 步与测试计划的 `WT` 一律使用当前工作树，不改测试计划里的路径。
   两条路径不要混用：对已经搬走函数的 runner 再跑抽取工具会报 `missing functions` 并退出 1。

1. （仅路径 A）用既有抽取工具生成模块与 probe runner：
```sh
uv run --no-project /tmp/pc-stage2-tools/extract_batch_v4.py \
  /tmp/pc-stage21/spec-b21-clean.json
```
spec 的字段为：`worktree` 指向新建的干净工作树，`module_name` 为 `_verify_chain`，`functions` 为上述 3 个，`constants` 为空，`load_anchor` 为 1200，`bind_after_line` 为 1384，`params` 为上述 6 个，`imports` 为 `import types`、`from datetime import datetime, timedelta, timezone`、`from pathlib import Path`、`from typing import Any`（`__future__` 由模板加在首行），`out_dir` 为 `/tmp/pc-stage21/clean-probe`。工具 144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`。本次路径 B 用的是已生成好的 `/tmp/pc-stage21/real-probe`（`spec-b21-real.json`），两者除 `worktree`／`out_dir` 外字段相同。

2. （仅路径 A）把生成的模块放进仓库，改 docstring 首行，再核对 129 行与模块 sha256：
```sh
cp /tmp/pc-stage21/clean-probe/_verify_chain.py \
  .apm/skills/professor-contact/scripts/_verify_chain.py
uv run --no-project python - <<'PY'
from pathlib import Path

path = Path(".apm/skills/professor-contact/scripts/_verify_chain.py")
lines = path.read_text().splitlines(keepends=True)
assert lines[1].startswith('"""Stage-2 helper module'), lines[1]
lines[1] = '"""Verify-cache helper module for ``contact_state.py``.\n'
path.write_text("".join(lines))
print("DOCSTRING RENAMED")
PY
wc -l .apm/skills/professor-contact/scripts/_verify_chain.py
shasum -a 256 .apm/skills/professor-contact/scripts/_verify_chain.py
sed -n '1,3p;22,23p' .apm/skills/professor-contact/scripts/_verify_chain.py
```
预期：`DOCSTRING RENAMED`；129 行；第 2 行是 `"""Verify-cache helper module for ``contact_state.py``.`；第 22 行为 `def build(*, read_json_file,`；sha256 为 `512acbead24f4550792131ebeed9afdede6d7f734ed8db364ae5d6a201dc27ea`。若跳过 docstring 这一步，模块会保持模板的 `Stage-2` 文案、sha 为 `23e962c7…`，与本计划后续断言不一致。

3. （仅路径 A）用 probe runner 覆盖 `contact_state.py`，按锚点收敛空行：
   - 加载块最后一行 `_VERIFY_CHAIN_SPEC.loader.exec_module(_verify_chain_module)` 之后、`def gap_job_block` 之前，probe 合并出的 7 行空行收敛为 2 行。
   - `render_fact_check_card = _stage5_email.render_fact_check_card` 与 `# Binding point:` 之间补 2 行空行（probe 里为 0 行）。
   - `verify_state = _verify_chain.verify_state` 之后、`def assemble_followup_draft` 之前，probe 的 3 行空行收敛为 2 行。
   只按上述文本锚点改动，不用行号 `sed`；加载块与绑定块的注释文字保持 probe 原文，只把加载块首行的 `Stage-2` 改成 `Verify-chain`。

4. 核对接缝、注释保留与 diff 内容：
```sh
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
git diff --stat
git diff --ignore-blank-lines -U0 -- .apm/skills/professor-contact/scripts/contact_state.py | grep -c '^@@'
git diff --ignore-blank-lines -- .apm/skills/professor-contact/scripts/contact_state.py | grep -c '^@@'
uv run --no-project python - <<'PY'
from pathlib import Path
import subprocess

base = subprocess.run(
    ["git", "show", "58c71c0:.apm/skills/professor-contact/scripts/contact_state.py"],
    check=True, capture_output=True, text=True).stdout.splitlines()
module = Path(".apm/skills/professor-contact/scripts/_verify_chain.py").read_text().splitlines()

removed = [line.strip() for line in base[1199:1297] if line.strip()]
start = next(i for i, line in enumerate(module) if line.strip().startswith("def _fingerprint_failure_kind"))
end = next(i for i, line in enumerate(module) if line.strip().startswith("return types.SimpleNamespace"))
moved = [line.strip() for line in module[start:end] if line.strip()]
assert removed == moved, "source text differs beyond indentation"
comments = [line for line in base[1199:1297] if line.lstrip().startswith("#")]
assert len(comments) == 12, len(comments)
print(f"SOURCE TEXT IDENTICAL ({len(moved)} lines, {len(comments)} comments)")
PY
```
预期：`1 file changed, 27 insertions(+), 98 deletions(-)` 与两组 hunk 计数 2 必须成立（本批不做格式重排）；`git diff` 的两个 hunk 头分别是 `@@ -1200,98 +1200,11 @@` 与 `@@ -1386,0 +1300,16 @@`；输出 `SOURCE TEXT IDENTICAL (94 lines, 12 comments)`。行数只记录，不作通过条件。

5. 逐字核对 docstring、自由名字与帮助输出：按 [test-plan.md](test-plan.md) 第 2、3、4 步执行（这三步负责生成 `base/`、`head/` 目录），不另写一套并行命令。

6. 按 [test-plan.md](test-plan.md) 执行全部 8 步，全部通过后再提交；提交内容只含 `contact_state.py`、`_verify_chain.py`、`plan/verify-chain/`，不夹带测试代码、Nix 或无关格式化。

## 验证方式

| 项目 | 命令或证据 | 通过标准 |
| --- | --- | --- |
| 结构与等价 | 测试计划第 1 步 | `T0 CHECKS PASS`：6 参数、3 成员、绑定顺序、加载约束、`FunctionDef` 计数 |
| 搬移等价 | 测试计划第 2 步 A/B 工具 | 23 条 `OK`（T0 3、T1 7、T2 6、T3 7），`ALL CHECKS PASS` |
| docstring 与自由名字 | 测试计划第 3 步 | `DOCSTRING CHECKS PASS`、`FREE NAMES OK`、源码文本与 12 行注释一致 |
| 入口 | 测试计划第 4 步 | `--help` 与父提交逐字节相同（3221 字节、`d622b7e6…`） |
| 业务 | 测试计划第 5、6 步 | T4 `Ran 3 tests`、`OK`；T5 `Ran 1 test`、`OK` |
| 接缝 | 测试计划第 7 步 | 2 个 hunk、`+27 −98`、67 个常量不变、diff 只含预期改动；行数只记录 |

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| verify 链以外的 `gap_job_block`、`assemble_followup_draft`、`load_validator_results`、legacy 迁移 helper、stage1 三件套 | 后续批次，本批只搬 3 个函数 |
| `verify_state` 的 escalation／conflict 分支新增业务断言 | 函数体 AST 与源码文本相同，T0 已核对注入的是 runner 自己的对象；现有 T4 覆盖成功、格式不兼容、mtime 漂移、过期 7 条路径 |
| 动态重绑定（导入后替换 6 个注入名）的支持 | 仓库内没有这类调用；本批把“导入时快照”写成冻结的内部约定，见影响分析 |
| 全量回归的逐条业务断言 | 仓库 CI 的 4 个 `shards` 与聚合 job `test` 覆盖，本清单只覆盖本批调用链 |
| Nix、README、测试代码 | 本批不涉及；Nix 整树复制的事实见影响分析 |

## 风险与反例

- 绑定不能提前到 `_stage5_email.build` 之前：`email_item_is_evidence_seeded` 与 `current_source_fingerprints` 那时还没有赋值，导入期会直接抛 `NameError`；`_stage5_email.build` 不接受 `verify_state` 参数是另一条独立的失败原因。
- 插入位置必须用文本锚点。按行号 1200 或 1386 直接插入，遇到上游新增行就会错位。
- 空行收敛必须用锚点：加载块后保留 7 行、别名后保留 3 行都会把 `+27 −98` 变成别的数字，而本批不做格式重排，所以这类偏差直接算失败。
- 注释不在 AST 里。只跑 A/B 工具会让 12 行 Issue-#10 注释被静默删除，所以第 4 步必须做源码文本核对。
- `EXPECTED_BASE` 与 `git rev-parse HEAD` 都输出 40 位完整 sha；写短 sha 会让比较直接失败。
- T4 必须跑完 3 个方法。只跑 `test_a` 会漏掉 `test_b` 的 4 个 subTest 和 `test_c` 的 mtime、31 天两条路径。
- 若在 `tests` 目录之外运行 `unittest`，`helpers` 不在导入路径上，测试会在收集阶段失败；所有业务测试都从 `tests` 目录执行。

## 实施前演练

在 `/tmp/pc-stage21` 的演练副本上已按上述步骤得到：`+27 −98`、2 个 hunk（R7 通过条件）；runner 2085 → 2014 行、模块 129 行（观察值）；A/B 23 条 `OK`（T0 3、T1 7、T2 6、T3 7）；docstring 统计为 `total=3 with_doc=1 multi=0 clean_equal=1 without_doc=2`；帮助 3221 字节、sha256 `d622b7e6…`；T4 `Ran 3 tests`、`OK`；T5 `Ran 1 test`、`OK`；顶层字面量 67 个不变；源码文本 94 行、注释 12 行逐行一致。演练中的模块 sha256 为 `512acbead24f4550792131ebeed9afdede6d7f734ed8db364ae5d6a201dc27ea`，runner sha256 为 `acc1ab20929c25376552c7f53bd2a48b5aad4331ec32ded9ce44f9e43a6fdcbb`（两个 sha 是观察值，模板或文案有意调整时记录新值）。`+27 −98` 与 2 个 hunk 若因模板或文案变化，属于范围或模板变更：先升版、重新测量，再按新值执行，不能直接拿执行记录覆盖。

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 第 1 版 | 2026-10-21 | 初稿：3 个函数搬入 `_verify_chain.py`，6 个注入名，+27 −98 |
| 第 2 版 | 2026-10-21 | 按第 1 版审核意见 B1–B5 与 N1–N6 修订：更正“区间内没有注释”为 12 行注释并加源码文本核对；补模块落盘步骤与 sha；删除重复的逐字核对步骤；补替代方案与影响分析（含闭包快照、`__module__`、仓库检索证据）；行数与 hunk 头降为观察值，R7 改为“diff 只含预期改动”；R2 补兄弟函数；更正提前绑定的失败类型为 `NameError`；step 0 改为核对带未提交改动的工作树；模块 docstring 与加载块首行改成 Verify-chain；补 Nix 整树复制的事实。 |
| 第 3 版 | 2026-10-21 | 按第 2 版复核意见 B1–B3 与 N1–N4 修订：实施步骤分成“路径 A 干净生成／路径 B 现有工作树核对”，第 2 步补模块 docstring 改写命令；hunk 数与 `+27 −98` 定为通过条件、行数降为记录；R2 改成“94 行非空源码去掉缩进后相同”；父提交说明改成基于 `972d4fd` 的准确表述；补 pickle 冻结约定；测试计划同步。 |
| 第 4 版 | 2026-10-21 | 按第 3 版复核意见 B1–B2 与 N1–N3 修订：路径 A 只把 `/tmp/pc-b21-clean` 当抽取源，抽取后复制回当前工作树，测试计划的 `WT` 不改；补 `spec-b21-clean.json` 的创建命令；实施前演练段只把行数与两个 sha 写成观察值，`+27 −98` 与 2 个 hunk 明确为 R7 通过条件，模板变化要升版重测。 |

## 审核状态

- 第 4 版：Proposed review status: pending（第 1 版意见 B1–B5／N1–N6、第 2 版意见 B1–B3／N1–N4、第 3 版意见 B1–B2／N1–N3 已修订；reviewer 已于 2026-10-21 给出 `Plan conclusion: APPROVED`，正式结论见其 Review record）。
- 测试计划：[test-plan.md](test-plan.md)，第 3 版。
- 复核通过后才能进入实施；复核意见若改变范围、绑定位置或验收数字，本计划升版，不沿用本版的实测值。
