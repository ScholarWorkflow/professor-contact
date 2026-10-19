# 测试分组与 CI 分片

本目录记录 CI 分片的依据与维护方式。`shards.json` 是唯一来源：它同时保存**每个测试模块的行为阶段**与分片分配，工作流与覆盖校验脚本都读它。

## 分组方法（按实际行为，不按文件名）

每个测试模块的阶段归属由**源码里的行为信号**决定：

1. CLI 子命令字符串（`"stage2-…"` 等）权重 3；
2. runner 入口点引用（`cmd_stageN_*`／`stageN_*`）权重 1；
3. 按测试类的继承关系合并基类信号——基类可能在别的模块里（例：`test_stage2_preflight_malformed` 继承 `test_stage2_preflight.PreflightBase`）。

模块取多数类的阶段作为主导阶段（按该类的方法数加权）；信号并列时记 `mixed:<a>+<b>`；完全没有阶段信号（文档/工具/夹具类）记 `non-stage`。文件名只作为分片的最小单位，不参与阶段判定。**每个模块的原始加权信号计数也保存在 `shards.json` 的 `signals` 字段里**（例如 `test_contact_state` 为 stage3 3550／stage5 3175／stage4 2200／stage2 1575／stage1 25，因此主导阶段记为 `stage3`），便于复核标签是否合理，而不是只看一个结论。

阶段含义：`stage1` = 候选采集（contact_stage1 / stage1-* 入口）；`stage2` = Stage 2 解析、preflight 与 handoff；`stage3` = Stage 3 渲染、校验与修正；`stage4` = Stage 4 选择与本地迁移；`stage5` = Stage 5 计划、finalize 与不可变包装；`non-stage` = 文档/工具/夹具类测试，不驱动某个阶段的运行时入口。

## 测量结果（目标修订 `6e624e0`，macOS／Python 3.14.7）

- 全套：`Ran 1025 tests in 416.2s`，失败 0、错误 0、跳过 1；
- 收集口径：`countTestCases()` = 1025；定义口径：156 个测试类 / 1033 个方法（脚本只数“带 ≥1 个 test 方法的类”且只数类体内定义的方法）；
- 脚本用**类名**做键，会合并同模块重名类（`Sample`）与跨模块重名类（`FakeTransport`），比严格 AST 计数少 2 类 2 方法。

## 分片（阶段分组驱动 + 耗时均衡）

分配规则：先按阶段分组，整组能放进某片的余量（均分份额 ×1.15）就整组放进去，放不下的大组（`stage3` 21 个模块）再按实测耗时贪心拆到负载最小的片。四片各 104.1s 左右（串行合计 416.0s）。

| 分片 | 模块数 | 模块耗时合计 | 阶段构成 |
| --- | --- | --- | --- |
| shard1 | 28 | 104.1s | mixed:stage2+stage3 1、non-stage 21、stage1 2、stage3 4 |
| shard2 | 14 | 104.1s | stage3 7、stage4 7 |
| shard3 | 12 | 103.8s | stage3 8、stage5 4 |
| shard4 | 24 | 104.0s | stage2 22、stage3 2 |

本地分片墙钟为 121／129／122／124s（旧分配），比模块耗时之和高出约 17%——多出的是每片一次性的 discover 与模块导入开销。首次 CI（ubuntu／Python 3.12，运行 `39168161446`）四片作业墙钟 1m27s／2m5s／2m12s／1m27s（含 checkout 与 setup-python），聚合任务 4s。

### 逐模块（秒 / 用例 / 分片 / 阶段）

| 模块 | 秒 | 用例 | 分片 | 阶段 |
| --- | --- | --- | --- | --- |
| test_contact_state | 82.8 | 88 | shard1 | stage3 |
| test_contact_evidence_ladder | 45.2 | 40 | shard2 | stage3 |
| test_stage3_validation_refine | 30.1 | 18 | shard3 | stage3 |
| test_issue66_validation_handoff | 28.9 | 12 | shard3 | stage3 |
| test_stage3_direction_groups | 28.4 | 19 | shard2 | stage3 |
| test_stage2_resolved_direction | 26.0 | 27 | shard3 | stage3 |
| test_stage2_style_validation_handoff | 19.3 | 7 | shard4 | stage2 |
| test_stage2_preflight | 17.5 | 34 | shard4 | stage2 |
| test_stage2_resolved_direction_downstream_regressions | 16.6 | 7 | shard4 | stage2 |
| test_stage3_direction_identity | 13.1 | 9 | shard2 | stage3 |
| test_stage5_immutable | 11.7 | 10 | shard3 | stage5 |
| test_issue66_stage3_local_state | 11.0 | 6 | shard1 | stage3 |
| test_issue61_direction_credibility_warning | 8.8 | 4 | shard2 | stage3 |
| test_resolved_direction_preflight_integration | 8.2 | 9 | shard4 | stage2 |
| test_stage2_facts_sidecar | 6.5 | 12 | shard4 | stage2 |
| test_build_issue29_stage2_fixture | 6.3 | 9 | shard4 | stage2 |
| test_stage2_zotero_rpc_transport | 6.2 | 22 | shard4 | stage2 |
| test_stage2_chatgpt_handoff | 4.5 | 22 | shard4 | stage2 |
| test_stage2_preflight_malformed | 4.2 | 6 | shard4 | stage2 |
| test_issue67_gate2_r3 | 3.8 | 6 | shard1 | stage3 |
| test_issue32_e2e_verifier | 3.7 | 52 | shard2 | stage4 |
| test_stage2_resolved_direction_fresh_review_regressions | 3.3 | 5 | shard4 | stage3 |
| test_issue81_verify_cache_contract | 3.1 | 3 | shard3 | stage5 |
| test_issue66_r12_validation_input_sha | 2.7 | 2 | shard2 | stage3 |
| test_stage5_fixture_isolation | 2.7 | 2 | shard3 | stage5 |
| test_stage2_preflight_binding | 2.6 | 4 | shard4 | stage2 |
| test_stage2_resolve_fingerprint_scope_regression | 2.4 | 3 | shard1 | stage3 |
| test_stage2_resolved_direction_regressions | 2.4 | 5 | shard4 | stage2 |
| test_stage2_resolved_direction_acceptance_boundary | 2.2 | 2 | shard1 | mixed:stage2+stage3 |
| test_stage2_input_router | 1.9 | 11 | shard4 | stage2 |
| test_stage2_narrative_example_contract | 1.8 | 4 | shard4 | stage3 |
| test_stage3_direction_identity_contract | 1.3 | 1 | shard2 | stage3 |
| test_stage2_chatgpt_handoff_review3 | 1.2 | 6 | shard4 | stage2 |
| test_issue55_stage3_runtime_assets | 0.8 | 16 | shard3 | stage3 |
| test_issue57_runtime_assets | 0.6 | 14 | shard4 | stage2 |
| test_opencode_depth_install | 0.6 | 11 | shard1 | non-stage |
| test_stage2_chatgpt_handoff_review4 | 0.5 | 2 | shard4 | stage2 |
| test_stage2_resolved_direction_merge_fulltext_regression | 0.5 | 1 | shard2 | stage3 |
| test_stage2_chatgpt_handoff_review5 | 0.4 | 3 | shard4 | stage2 |
| test_stage5_dualtarget_contract | 0.4 | 14 | shard3 | stage5 |
| test_issue74_cli_compat | 0.3 | 3 | shard2 | stage4 |
| test_stage1_candidates | 0.3 | 36 | shard1 | non-stage |
| test_contact_targets | 0.2 | 45 | shard1 | non-stage |
| test_issue32_eval_request | 0.2 | 21 | shard1 | non-stage |
| test_prepare_issue39_stage2_fixture | 0.2 | 6 | shard1 | non-stage |
| test_prepare_issue40_runtime_fixture | 0.2 | 10 | shard1 | non-stage |
| test_build_issue32_e2e_fixture | 0.1 | 7 | shard1 | non-stage |
| test_issue40_r2_verifier | 0.1 | 5 | shard3 | stage3 |
| test_issue57_routing_stability | 0.1 | 43 | shard2 | stage4 |
| test_stage1_handoff_identity | 0.1 | 3 | shard1 | stage1 |
| test_apm_deployment_metadata | 0.0 | 28 | shard4 | stage2 |
| test_codex_native_delegation_contract | 0.0 | 52 | shard3 | stage3 |
| test_contact_targets_gate2_oracle | 0.0 | 1 | shard1 | non-stage |
| test_fixture_support | 0.0 | 16 | shard2 | stage4 |
| test_gate2_evidence | 0.0 | 4 | shard4 | stage2 |
| test_issue39_eval_request | 0.0 | 7 | shard1 | non-stage |
| test_issue51_delegation_verifier | 0.0 | 26 | shard1 | non-stage |
| test_issue51_standalone_runtime_recipe | 0.0 | 16 | shard1 | non-stage |
| test_issue53_stage4_runtime_assets | 0.0 | 8 | shard2 | stage4 |
| test_issue65_gate2_r24_regressions | 0.0 | 2 | shard3 | stage3 |
| test_issue66_validator_report_contract | 0.0 | 3 | shard1 | non-stage |
| test_issue67_riso_case_prep | 0.0 | 2 | shard1 | non-stage |
| test_issue67_runtime_config | 0.0 | 4 | shard2 | stage4 |
| test_issue67_runtime_evidence | 0.0 | 4 | shard1 | non-stage |
| test_issue68_eval_request | 0.0 | 6 | shard1 | non-stage |
| test_issue74_static_acceptance | 0.0 | 4 | shard1 | non-stage |
| test_p47_target_isolation | 0.0 | 3 | shard1 | non-stage |
| test_seed_issue39_zotero | 0.0 | 8 | shard1 | non-stage |
| test_stage01_caller_contract | 0.0 | 20 | shard1 | stage1 |
| test_stage1_stage2_contract | 0.0 | 14 | shard4 | stage2 |
| test_stage1_stage2_contract_gate2_oracle | 0.0 | 1 | shard4 | stage2 |
| test_stage2_chatgpt_handoff_review | 0.0 | 2 | shard4 | stage2 |
| test_stage2_reference_id_repair_contract | 0.0 | 4 | shard1 | non-stage |
| test_stage2_zotero_endpoint_contract | 0.0 | 9 | shard4 | stage2 |
| test_stage3_stage4_caller_contract | 0.0 | 27 | shard3 | stage3 |
| test_stage4_selection_agent_contract | 0.0 | 17 | shard2 | stage4 |
| test_stage5_template_body | 0.0 | 9 | shard1 | non-stage |
| test_verify_issue39_endpoint_runtime | 0.0 | 21 | shard1 | non-stage |

## 覆盖与映射保证

`scripts/check_test_shards.py`（仓库根）枚举 `.apm/skills/professor-contact/tests/test_*.py`，并断言：

1. 每个发现的模块恰好属于一个分片；
2. 清单里的模块都有对应文件（拼写错误会失败）；
3. 没有分片是空列表；
4. **每个模块都带阶段**，且阶段值属于文档化的取值集合（`stage1`…`stage5`／`non-stage`／`mixed:*`）。

CI 里 `shards` matrix 的每一片都先跑这个校验；新增测试模块若忘了归类，或阶段字段缺失/写错，CI 直接失败而不是静默漏跑。

## CI 形态

- `shards`：matrix `[shard1, shard2, shard3, shard4]`，`fail-fast: false`；每片先校验、再从 `tests/` 目录跑本片模块；
- `test`：聚合任务（`needs: [shards]`、`if: always()`），`needs.shards.result != success` 即失败——分支保护里的必需检查名仍是 `test`。

## 维护约定

- 新增或删除测试模块后，更新 `shards.json`（含阶段）并本地跑 `python scripts/check_test_shards.py`；
- 首次 CI 跑完后，用 ubuntu／Python 3.12 的实测秒数更新 `shards.json` 的 `seconds` 与本文件的墙钟列；
- 本机（macOS／3.14.7）与 CI（ubuntu／3.12）耗时不同，均衡只保证相对接近。
