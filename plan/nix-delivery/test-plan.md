# professor-contact Nix 测试计划

- Test plan revision: TP2（2026-10-17；仅同步 scripts 固定入口路径，N1–N4 不变），关联 [执行计划 R2](implementation-plan.md)。
- Proposed review status: pending；Gate1 必测清单、Gate2 recipe、Gate3 结果均待独立审核。当前没有实现，全部未执行，不声明 PASS。
- 产品基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`；执行时记录真正待验实现SHA与锁定依赖。只验本次 aarch64-darwin / Codex 安装和必要入口，不扩 Stage0–5 业务回归。

## 1. 必测清单（上限）

| ID | 目标/输入 | 预期 | 检查方式 |
|---|---|---|---|
| N1 | 固定提交的 runtime、完整 agent、environment | Darwin实际build；完整包由真实依赖组成，默认codex且包级可override | nix build实际结果；读结构化agent-env元数据，override求值不另建安装矩阵 |
| N2 | 一个仓库外新consumer实际apply，含无关sentinel技能 | 完整skill/scripts/docs/8个角色/Stage5附录；必要依赖和MCP正确归属，sentinel保留 | 文件与source静态比对、TOML/JSON解析；共同源入口适配以外正文无业务改写。共享冲突/删除/继承/回滚测试引用原共享证据，不重跑 |
| N3 | 从安装scripts薄入口执行小型preview正常输入及router已有PDF；handoff helper固定调用 | runner实际产生预期业务JSON，资源/同目录import可达；helper使用固定环境及同一paper安装，原uv默认非Nix路径保留 | 下述本地最小动作+完整diff检查。handoff受影响的既有确定性测试按原fixture复用，只选_run_future_work/facts locator相关测试，不跑完整ZIP/模型流程 |
| N4 | 安装角色一次真实Codex调用；router一次真实Zotero摘要导出 | named角色可用且遵守原输入边界；缺PDF记录得到规范化JSON，非FileNotFoundError | 原生调用返回业务结果；按PR90真实摘要recipe复用服务准备，消费实际导出文件。不把help或mock当完成 |

这些目标来自Nix共识最小验收。N3不要求新建判定器、无异常组合穷举。N4不下载论文、不调用OCR模型、不导入KB、不发邮件；collector/browser/KB未变服务行为及共享MCP结果直接复用有效上游记录。若固定入口改动影响某个上游结果，明确那一入口后补相应最小动作，不自动增加完整服务矩阵。

## 2. 环境、准备与复用

由本地执行者使用 aarch64-darwin Nix+既有Codex eval服务。此文不授权现在安装/运行。执行者从获审实现提交确定 `CONTACT_REF=github:ScholarWorkflow/professor-contact/<实际40位SHA>`，把它记入结果；不能拿此纯计划SHA构建，不能使用path input、手拷贝技能或开发checkout修补consumer。

准备单个仓库外临时目录，例如 `RUN=$(mktemp -d /tmp/contact-nix.XXXXXX)`；consumer=`$RUN/consumer`，业务样本=`$RUN/data`，输出=`$RUN/output`；分别mkdir。保持现有HOME，不抹掉Nix认证；必要时独立CODEX_HOME，使用既有eval配置/账号，不读eval自身配置查信任列表。测试服务如需Zotero必须使用已授权的独立测试库和loopback端点，不能读取生产库。缺平台、collector/knowledge实际包、服务/模型配置就标对应项未执行/无法判断，其余独立项继续。

只N2要求一次新安装；后续全部用同一个有效consumer。文档更新不重装；重试仅重置本项可变样本，不清用户目录或全局缓存。

## 3. Recipe

### N1 / N2：构建及实际安装

实现发布后执行：

```sh
nix build "$CONTACT_REF#professor-contact-runtime" --out-link "$RUN/runtime"
nix build "$CONTACT_REF#professor-contact" --out-link "$RUN/package"
nix build "$CONTACT_REF#professor-contact-environment" --out-link "$RUN/environment"
mkdir -p "$RUN/consumer/.agents/skills/unrelated-sentinel"
printf 'keep\n' > "$RUN/consumer/.agents/skills/unrelated-sentinel/marker"
"$RUN/environment/bin/agent-env" apply --project "$RUN/consumer"
```

读 `$RUN/package/agent-env.json`（jq）及 `.codex/agents/*.toml`（TOML parser），确认professor-contact及七个stage角色唯一、analyzer为Codex源。用flake输出的 `professor-contact.override { enableHarnesses = []; }` 的 `passthru.agentEnv.enableHarnesses` 求值为空列表即可，不再启动第二套服务。命令为 `export CONTACT_REF; nix eval --json --impure --expr 'let f = builtins.getFlake (builtins.getEnv "CONTACT_REF"); in (f.packages.aarch64-darwin.professor-contact.override { enableHarnesses = []; }).passthru.agentEnv.enableHarnesses'`，预期 `[]`。

人工比对完整源目录与安装树；允许差异仅R2必要同目录薄入口、固定运行环境与原文附录。检查 `.agents/skills/professor-contact/scripts/_stage2_chatgpt_handoff_impl.py`、stage5_immutable.py、docs/stage5-legacy-contract.md存在，Stage5路由附录实际进入SKILL与coordinator正文；检查sentinel仍为keep。读依赖元数据确认collector/ contact-evidence、paper、Zotero、humanizer、vision、pdfx的llm-ocr-refresh、KB所选包真实递归安装；不同payload冲突不能记录成成功。

只核此环境具体生成的必要MCP表与上游正式输出相符，不重验共享installer保护全矩阵。模型/网络/审批保持既有设置。build/eval/apply分别记录，eval成功不能替代build。

### N3：实际本地入口

在 `$RUN/data/方向预筛.json` 写入以下合成输入（不借用真实教授资料）：

```json
{"professor":"安装样本教授","preview_fingerprint":"nix-fixture","preview_fingerprint_version":"v1","direction_id_version":"v1","membership_mode":"overlap_allowed","directions":[{"direction_id":"dir_fixture","member_fingerprint":"m1","name_ja":"例","name_zh":"样本方向","summary_zh":"安装检查","members":[{"item_key":"NIXTEST1","preview_confidence":"high"}],"representatives":[]}]}
```

```sh
SKILL="$RUN/consumer/.agents/skills/professor-contact"
"$SKILL/scripts/contact_targets" preview --preview "$RUN/data/方向预筛.json" > "$RUN/output/preview.json"
```

jq读取status为ok、教授为安装样本教授，options中方向ID为dir_fixture、paper_count=1。预期业务值固定；不能根据失败输出更改期望。

再用现有上游小型PDF fixture绝对路径写 `[ {"item_key":"NIXTEST1","pdf_path":"<fixture绝对路径>"} ]` 到papers.json，执行：

```sh
"$SKILL/scripts/stage2_input_router" --papers "$RUN/data/papers.json" --output-dir "$RUN/output/router" > "$RUN/output/routes.json"
```

确认NIXTEST1选中该PDF，不触发摘要导出；文件路径/空格通过argv传递。该项检查安装入口，不检查PDF抽取准确性。

handoff内部固定Python前缀及facts同目录适配是N3的一部分：执行工程师从现有 `test_stage2_chatgpt_handoff*.py` 中选出直接覆盖该适配的既有 `test_stage2_chatgpt_handoff.HandoffTests.test_future_work_selection_is_finalized_locally_via_uv_run`，复用其合法facts/future-work数据，补覆盖本次新增固定Python后端的对应调用断言并写明安装路径；保留旧uv默认断言，新增的固定Python断言仅覆盖本次适配，不把fake helper结果当真实导出验收。不要以扩大到全部handoff suite代替定位。安装态执行该既有fixture的准确命令尚待实现后补入，故这一小段Gate2待补，不能声称步骤已完全可执行。

### N4：角色和真实导出

1. 用原有eval服务及其README调用方式，在command中传 `--sandbox workspace-write --cd <本consumer绝对路径>`，配置使用既有gpt-6-luna/low默认profile。从当前会话实际原生调用安装的 `professor-contact-selection`，只传 `folder_path` 指向临时样本、缺selection；等待其按原合同返回needs_input/pending_selection（需现有有效Stage3 fixture，不能额外创造业务事实兜底）。检查一次该角色实际结果即可，不循环调用8角色、不测试整套委派拓扑。精确fixture准备与eval请求JSON沿用已有效的contact selection recipe；本计划尚未取得该recipe定位，Gate2在执行前必须补上路径/版本/准备命令，不把它留给用户猜。
2. 真实摘要导出沿用 [PR90 macOS recipe](../pr90-macos-real-abstract-export-recipe.md) 已批准的独立Zotero测试库/服务准备与已存在有摘要无PDF的单条item key。只执行该recipe的服务准备与一条router导出，替换本项入口为安装的 `$SKILL/scripts/stage2_input_router`；不执行该recipe的其它APM重装/完整测试。papers.json包含该已知测试key且不含pdf/ocr路径。预期router行返回 carrier=abstract_json、level=abstract、status=ok，并写出包含该key、预置标题/摘要的规范化文件；jq检查真实产物。传递recipe既有ZOTERO_HTTP_URL/ZOTERO_MCP_URL；不绕过正式Zotero脚本、不得mock代替真实导出。服务不具备时该子项记未执行，不能拿N3 PDF路由充数。

## 4. 结果、重试和关闭

当前N1–N4全部未执行；Gate1/Gate2 pending。上述明确标出的recipe空缺由测试执行工程师在正式执行前补入本文件，审核只补核该处与连带影响，不增加测试目标。执行计划可以先进入draft评审，不谎称这些未来操作已经完成。

记录每项产品SHA、依赖pin、实际命令、结果、必要输出位置以及复用证据即可。引用共享agent-env TP1.1/Gate1/Gate2和上游已验结果，不自授PASS。未运行的OCR/真实论文分析/KB写入/下载/全套磁流程不能宣称通过。

网络拉取或外部服务短暂故障恢复后允许同参数重试一次；业务断言失败先修复，不重复采样。Zotero只读导出，确认本次输出目录隔离后再重试，保留旧失败记录；不修改全局安全设置。没有新信息的持续外部故障停止受影响项。运行完成且无子线程使用后，只删除本次临时可变fixture，结果保留给审核；不终止用户进程、不清生产库。

