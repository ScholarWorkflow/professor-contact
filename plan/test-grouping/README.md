# 测试分组与 CI 分片

本目录记录 CI 分片的依据与维护方式。分片清单 `shards.json` 是唯一来源，工作流与覆盖校验脚本都读它。

## 分组方法（不按文件名）

每个测试模块的阶段归属由**源码里的行为信号**决定，与文件名无关：

1. CLI 子命令字符串（`"stage2-…"` 等）权重 3；
2. runner 入口点引用（`cmd_stageN_*`／`stageN_*`）权重 1；
3. 按测试类的继承关系合并基类信号——基类可能在别的模块里（例：`test_stage2_preflight_malformed` 继承 `test_stage2_preflight.PreflightBase`）。

文件名只用作“分片的最小单位”，不参与阶段判定。测量脚本：主检出 `.tmp_scripts/1020_test_stage_map2.py`（仓库外一次性脚本）。

## 测量结果（目标修订 `6e624e0`，macOS／Python 3.14.7）

- 全套：`Ran 1025 tests in 416.2s`，失败 0、错误 0、跳过 1；
- 收集口径：`countTestCases()` = 1025；
- 定义口径：156 个测试类 / 1033 个方法（脚本只数“带 ≥1 个 test 方法的类”且只数类体内定义的方法，与收集口径不同）；
- 阶段分布（方法数）：stage3 347、无阶段信号 250、stage2 239、stage4 143、stage5 29、stage1 23、跨阶段混合 2；
- 脚本用**类名**做键，会合并同模块重名类（`Sample`）与跨模块重名类（`FakeTransport`），比严格 AST 计数少 2 类 2 方法。

## 分片

按模块耗时降序贪心装箱分成 4 片，各片模块耗时合计 104.0s（串行合计 416.2s）。
本地分片墙钟为 121／129／122／124s，比模块耗时之和高出约 17%——多出的是每片一次性的 discover 与模块导入开销（四片最大/最小 ≈ 1.06），两个数字口径不同，不矛盾。

| 分片 | 模块数 | 模块耗时合计 | 实测墙钟（本地） |
| --- | --- | --- | --- |
| shard1 | 38 | 104.0s | 见测试执行记录 |
| shard2 | 13 | 104.0s | 见测试执行记录 |
| shard3 | 14 | 104.0s | 见测试执行记录 |
| shard4 | 13 | 104.0s | 见测试执行记录 |

### 逐模块耗时（秒 / 用例数 / 所属分片 / 主导阶段）

| 模块 | 秒 | 用例 | 分片 | 主导阶段 |
| --- | --- | --- | --- | --- |
| test_contact_state | 82.8 | 88 | shard1 | - |
| test_contact_evidence_ladder | 45.2 | 40 | shard2 | - |
| test_stage3_validation_refine | 30.1 | 18 | shard3 | - |
| test_issue66_validation_handoff | 28.9 | 12 | shard4 | - |
| test_stage3_direction_groups | 28.4 | 19 | shard4 | - |
| test_stage2_resolved_direction | 26.0 | 27 | shard3 | - |
| test_stage2_style_validation_handoff | 19.3 | 7 | shard2 | - |
| test_stage2_preflight | 17.5 | 34 | shard3 | - |
| test_stage2_resolved_direction_downstream_regressions | 16.6 | 7 | shard4 | - |
| test_stage3_direction_identity | 13.1 | 9 | shard2 | - |
| test_stage5_immutable | 11.7 | 10 | shard3 | - |
| test_issue66_stage3_local_state | 11.0 | 6 | shard4 | - |
| test_issue61_direction_credibility_warning | 8.8 | 4 | shard2 | - |
| test_resolved_direction_preflight_integration | 8.2 | 9 | shard1 | - |
| test_stage2_facts_sidecar | 6.5 | 12 | shard4 | - |
| test_build_issue29_stage2_fixture | 6.3 | 9 | shard3 | - |
| test_stage2_zotero_rpc_transport | 6.2 | 22 | shard2 | - |
| test_stage2_chatgpt_handoff | 4.5 | 22 | shard1 | - |
| test_stage2_preflight_malformed | 4.2 | 6 | shard4 | - |
| test_issue67_gate2_r3 | 3.8 | 6 | shard3 | - |
| test_issue32_e2e_verifier | 3.7 | 52 | shard2 | - |
| test_stage2_resolved_direction_fresh_review_regressions | 3.3 | 5 | shard3 | - |
| test_issue81_verify_cache_contract | 3.1 | 3 | shard1 | - |
| test_issue66_r12_validation_input_sha | 2.7 | 2 | shard4 | - |
| test_stage5_fixture_isolation | 2.7 | 2 | shard2 | - |
| test_stage2_preflight_binding | 2.6 | 4 | shard4 | - |
| test_stage2_resolve_fingerprint_scope_regression | 2.4 | 3 | shard1 | - |
| test_stage2_resolved_direction_regressions | 2.4 | 5 | shard3 | - |
| test_stage2_resolved_direction_acceptance_boundary | 2.2 | 2 | shard2 | - |
| test_stage2_input_router | 1.9 | 11 | shard4 | - |
| test_stage2_narrative_example_contract | 1.8 | 4 | shard1 | - |
| test_stage3_direction_identity_contract | 1.3 | 1 | shard3 | - |
| test_stage2_chatgpt_handoff_review3 | 1.2 | 6 | shard2 | - |
| test_issue55_stage3_runtime_assets | 0.8 | 16 | shard3 | - |
| test_issue57_runtime_assets | 0.6 | 14 | shard2 | - |
| test_opencode_depth_install | 0.6 | 11 | shard1 | - |
| test_stage2_chatgpt_handoff_review4 | 0.5 | 2 | shard4 | - |
| test_stage2_resolved_direction_merge_fulltext_regression | 0.5 | 1 | shard2 | - |
| test_stage2_chatgpt_handoff_review5 | 0.4 | 3 | shard3 | - |
| test_stage5_dualtarget_contract | 0.4 | 14 | shard4 | - |
| test_issue74_cli_compat | 0.3 | 3 | shard1 | - |
| test_stage1_candidates | 0.3 | 36 | shard2 | - |
| test_contact_targets | 0.2 | 45 | shard3 | - |
| test_issue32_eval_request | 0.2 | 21 | shard1 | - |
| test_prepare_issue39_stage2_fixture | 0.2 | 6 | shard4 | - |
| test_prepare_issue40_runtime_fixture | 0.2 | 10 | shard2 | - |
| test_build_issue32_e2e_fixture | 0.1 | 7 | shard3 | - |
| test_issue40_r2_verifier | 0.1 | 5 | shard1 | - |
| test_issue57_routing_stability | 0.1 | 43 | shard3 | - |
| test_stage1_handoff_identity | 0.1 | 3 | shard4 | - |
| test_apm_deployment_metadata | 0.0 | 28 | shard1 | - |
| test_codex_native_delegation_contract | 0.0 | 52 | shard1 | - |
| test_contact_targets_gate2_oracle | 0.0 | 1 | shard1 | - |
| test_fixture_support | 0.0 | 16 | shard1 | - |
| test_gate2_evidence | 0.0 | 4 | shard1 | - |
| test_issue39_eval_request | 0.0 | 7 | shard1 | - |
| test_issue51_delegation_verifier | 0.0 | 26 | shard1 | - |
| test_issue51_standalone_runtime_recipe | 0.0 | 16 | shard1 | - |
| test_issue53_stage4_runtime_assets | 0.0 | 8 | shard1 | - |
| test_issue65_gate2_r24_regressions | 0.0 | 2 | shard1 | - |
| test_issue66_validator_report_contract | 0.0 | 3 | shard1 | - |
| test_issue67_riso_case_prep | 0.0 | 2 | shard1 | - |
| test_issue67_runtime_config | 0.0 | 4 | shard1 | - |
| test_issue67_runtime_evidence | 0.0 | 4 | shard1 | - |
| test_issue68_eval_request | 0.0 | 6 | shard1 | - |
| test_issue74_static_acceptance | 0.0 | 4 | shard1 | - |
| test_p47_target_isolation | 0.0 | 3 | shard1 | - |
| test_seed_issue39_zotero | 0.0 | 8 | shard1 | - |
| test_stage01_caller_contract | 0.0 | 20 | shard1 | - |
| test_stage1_stage2_contract | 0.0 | 14 | shard1 | - |
| test_stage1_stage2_contract_gate2_oracle | 0.0 | 1 | shard1 | - |
| test_stage2_chatgpt_handoff_review | 0.0 | 2 | shard1 | - |
| test_stage2_reference_id_repair_contract | 0.0 | 4 | shard1 | - |
| test_stage2_zotero_endpoint_contract | 0.0 | 9 | shard1 | - |
| test_stage3_stage4_caller_contract | 0.0 | 27 | shard1 | - |
| test_stage4_selection_agent_contract | 0.0 | 17 | shard1 | - |
| test_stage5_template_body | 0.0 | 9 | shard1 | - |
| test_verify_issue39_endpoint_runtime | 0.0 | 21 | shard1 | - |

## 覆盖保证

`scripts/check_test_shards.py`（仓库根）枚举 `.apm/skills/professor-contact/tests/test_*.py`，并断言：

1. 每个发现的模块恰好属于一个分片；
2. 清单里的模块都有对应文件（拼写错误会失败）；
3. 没有分片是空列表。

CI 里 `shards` matrix 的每一片都先跑这个校验；新增测试模块若忘了归类，CI 直接失败而不是静默漏跑。

## CI 形态

- `shards`：matrix `[shard1, shard2, shard3, shard4]`，`fail-fast: false`；每片先校验、再从 `tests/` 目录跑本片模块；
- `test`：聚合任务（`needs: [shards]`、`if: always()`），`needs.shards.result != success` 即失败——分支保护里的必需检查名仍是 `test`。

## 维护约定

- 新增或删除测试模块后，更新 `shards.json` 并本地跑 `python scripts/check_test_shards.py`；
- 首次 CI 跑完后，用 ubuntu／Python 3.12 的实测秒数更新 `shards.json` 的 `seconds` 与本文件的墙钟列；
- 本机（macOS／3.14.7）与 CI（ubuntu／3.12）耗时不同，均衡只保证相对接近。
