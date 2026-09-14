# Issue #40 canonical runtime matrix（R1–R4）

本目录是 `ScholarWorkflow/professor-contact#32` 运行时验证在 issue `#40`
测试边界重构后的 canonical recipe 落地。旧 E0–E7 细粒度业务 gate（Stage 0
selection preview、collector payload contract、fingerprint、模板占位符、
validation schema 等）**明确 superseded**：这些规则已回归 deterministic unit
tests（`tests/test_*.py`），runtime 只保留必须经过真实 Codex/eval harness 才能观察的内容。

## 权威来源

完整 Test Recipe（common setup、执行命令、evidence 布局、机械 verdict）以
issue `#40` 第 5 节为权威；本 README 不复制其步骤，避免双源漂移。

## Cases

| Case | 证明 | verifier 入口 |
| --- | --- | --- |
| `install` | clean consumer 正式安装、resolved SHA 指纹 | `verify_issue32_e2e.py --case install` |
| `r1` | Stage 1 cross-repo nested delegation（`root -> child -> grandchild`）+ Stage 1 artifact + Stage 2 正式 loader 消费 | `--case r1` |
| `r2` | Stage 2 最深嵌套（至少 `root -> L1 -> L2 -> L3`）+ Stage 2 artifact + Stage 3 正式 plan loader 消费 | `--case r2` |
| `r3a` | Stage 3 root 至少两个 formal sibling children + Stage 3 canonical state | `--case r3a` |
| `r3-pre-omit` | Stage 4 omission 前 `套磁选择.json`/`邮件输入.json` 不存在的 file-state 证据 | `--case r3-pre-omit` |
| `r3b` | Stage 4 omission 后仍不存在（pre/post no-write） | `--case r3b --pre-state ...` |
| `r4a` | 固定机械 selection 被精确消费 + Stage 4 canonical selection/email pack | `--case r4a --selection-input ...` |
| `r4b` | Stage 5 nested formal delegation + 初回/follow-up canonical artifacts | `--case r4b` |

## 资产

- `prompts/issue40-r{1,2,3a,3b,4a,4b}.txt` — 版本控制的固定 prompt；只允许
  机械替换 `${PROGRAM_ROOT}` / `${SELECTION_FILE}`，执行 agent 不得改写。
- `prepare_issue40_runtime_fixture.py` — 唯一的 R1 setup helper（动态 Zotero
  keys + deterministic PDF attachment + Stage 0 canonical target + setup evidence）。
- `build_issue32_e2e_fixture.py` — 底层 raw-input builder，绑定 helper 返回的
  真实 disposable-Zotero item/attachment keys；硬编码 `AAAA1111`/`BBBB2222`
  一律拒绝。
- `build_issue32_eval_request.py` — canonical 请求默认：无 Chrome、
  `workspace-write + network_access=true`、Zotero env 注入；`--enable-chrome`
  仅为未来 browser-specific recipe 保留的 opt-in。
- `verify_issue32_e2e.py` — 只读 verifier：产品状态零写入，只写调用者指定的
  `--output` 路径（verdict 文件与 `--make-stage4-selection` 的 selection 文件，
  均在产品状态之外）。verdict status：`pass` / `fail` /
  `not_tested`（observability gap，不是 pass）/ `invalid_evidence` /
  `blocked`；只有 `pass` 退出码为 0。

## 固定的机械 selection policy

`make-stage4-selection` 冻结为 `lexicographic-first-candidate-id`：在指定
direction 的 canonical Stage 3 state 中按 `candidate_id` 字典序排序取第一项；
执行者不得自行挑选 candidate。
