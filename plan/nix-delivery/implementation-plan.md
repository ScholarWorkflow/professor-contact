# professor-contact Nix 交付执行计划

- Plan revision: R3（2026-10-17；在 R2 同目录薄入口方案中补齐 Stage 5 immutable finalize 入口）
- Proposed review status: pending
- Requirement revision: 用户本轮授权的五项 Nix 计划交付；[Nix skill 交付规则](https://app.notion.com/p/3fb0101a85f38185b17adb417590e50e)，2026-10-16 12:19 UTC 版本。
- Target repository revision: `305bc08f8b186672108cffbba0293d249bc8b4b2`（main）。此 PR 只有执行/测试计划，没有实现或测试结果。
- 本文是唯一执行计划；测试范围与步骤见同目录 [test-plan.md](test-plan.md)。[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[计划审核规则](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[测试规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 分别约束操作、方案审核、测试。

## 1. 目标与边界

新增 aarch64-darwin / Codex 的完整 producer 包：项目 flake 选中 professor-contact 后，通过共享 agent-env-nix 实际复制完整 skill、原生角色及真实直接依赖，必要入口使用固定运行环境。保留 APM、uv/PEP723 和原来的 Stage 0–5 业务语义。

本任务不改下载策略、证据等级、缓存、分析归属、时效、生成邮件、用户选择或委派拓扑。不把 PR91/92 的业务修复合并变成本安装包的全局前置；不处理已暂缓的 paper-analysis 跨页引文。浏览器路径/动态端口问题只影响实际下载调用链，不阻纯本地 runner。Linux/OpenCode 不在本轮新交付承诺中；不把 Darwin 求值说成实际 build。

## 2. 现状与设计依据

1. [apm.yml](../../apm.yml) 的六个 repo 级依赖仅作线索。实际 Nix 边按 [Codex analyzer](../../packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md)、[downloader](../../.apm/agents/professor-contact-downloader.agent.md)、[email-generator](../../.apm/agents/professor-contact-email-generator.agent.md) 的调用选择，不能照搬整个 repo。
2. [.apm/skills/professor-contact](../../.apm/skills/professor-contact) 是唯一 skill 源，含 scripts、docs、测试和资源。当前模板属于用户 program root；安装不得生成、改写或覆盖用户邮件模板/profile/业务状态。依赖边界见 [dependency-runtime-boundaries.md](../../.apm/skills/professor-contact/docs/dependency-runtime-boundaries.md)。
3. `stage2_input_router.py` 默认用 argv `uv run <loaded zotero-read>/scripts/zotero_item_export.py`，已有 `--exporter` 单 executable 入口。`_stage2_chatgpt_handoff_impl.py::_run_future_work` 同样用 uv；`_facts_script` 从同目录解析 facts.py。因此仅把 Python/uv 列入 runtimePackages 不会解决固定入口；完整复制后仍要绑定这些实际子进程。
4. `contact_state.py::upstream_check_script` 优先显式 locator，其次已安装 sibling `professor-collector/scripts/contact_evidence.py`；它不能由用户 program root 推导。保留这一正式 owner/失败语义。
5. 当前共享 [agent-env-nix](https://github.com/RekiDunois/agent-env-nix) 提供 mkAgentPackage / mkProject，exports 为 skills/agents；角色原生内容为 name、description、developer_instructions。它不替 producer 注入 PATH，也不注册任意 `.instructions.md`。
6. [email-generator](../../.apm/agents/professor-contact-email-generator.agent.md) 的 Stage 5 最终提交仍调用 `skillrepo exec professor-contact .apm/skills/professor-contact/scripts/stage5_immutable.py stage5-finalize ...`；[stage5_immutable.py](../../.apm/skills/professor-contact/scripts/stage5_immutable.py) 在脚本所在目录解析相邻 `contact_state.py`，并以 `sys.executable` 启动计划、临时 provenance 副本和最终提交。Nix 安装不能依赖 `skillrepo` 注册表或源码 checkout；缺少这条同目录固定入口会使 Stage 5 最终生成链不完整。依据为本段两份源文件及上述目标仓库 revision。

## 3. 公开输出与闭包

未来新增 `flake.nix`、`flake.lock`、薄 `nix/contact.nix` 和 README 安装说明；不在 nix/ 保存第二份业务正文。输出：

- `packages.aarch64-darwin.professor-contact-runtime`：固定 Python runner 与完整自有资源的普通 derivation；可先构建，不冒充完整 agent 安装。
- `packages.aarch64-darwin.professor-contact`：mkAgentPackage，id `professor-contact`，默认 `enableHarnesses = [ "codex" ]`，通过真实 override 可关闭本包投影。
- `packages.aarch64-darwin.professor-contact-environment`：mkProject，roots = [ professor-contact ]；下游可直接用前项与其他顶层包组合，无需 APM。

直接 agent 依赖冻结为：

| 对象 | 原因与 owner | 接入状态 |
|---|---|---|
| professor-research 的 professor-collector | Stage1 missing item-key PDF fill；Stage5 contact-evidence checker/资源 | 同批计划拟公开 `packages.aarch64-darwin.professor-collector`（id professor-research-collector），尚待实现。最终 pin 实际输出提交；不得拿 explainer 包冒充 |
| paper-analysis | Stage2 named paper-analysis、future_work/facts helpers | `packages.aarch64-darwin.paper-analysis`，已合入 PR20；固定实际 merge `eceade6b6d22a6114ecdd99b5a0c358869dfc798` |
| zotero-tools | 元数据/摘要导出、session | `packages.aarch64-darwin.zotero-tools`，`24eb6cf596c082ac005ccdd800b962fbb6a8e2c8` |
| base humanizer-ja / vision-tools | Stage5 动态字段润色 / Stage2 OCR机制 | `3ab2ac188e625b8a8ae37b5fa318c579787c3d1e` 对应同名 packages；vision 同时也是 paper 依赖，必须复用同一个对象，避免不同 payload 同名冲突 |
| pdf-processing-core pdfx-agent | analyzer 明确加载 llm-ocr-refresh | `3444dca0e0b84f46d1839ab5c707afa78e23d3a7` 的 `packages.aarch64-darwin.pdfx-agent` 确实导出该 skill；其已定义包粒度含 formula-repair，不另拆或复制上游资源 |
| knowledge extraction-to-knowledge | 原 `kb_import=true` 路径，递归 kb-importer / runtime | 同批 knowledge owner 拟公开 `lib.mkKnowledgePackages { pkgs; enableHarnesses = [ "codex" ]; }` 返回的 `extraction-to-knowledge`，递归使用同工厂的 kb-importer / personal-knowledge-runtime；接口待实现，当前 knowledge-importer 是 mkProject，不能当 agentDependencies |

professor-topic-clustering 的 preview 是既有输入边界，contact 不负责从零生成 preview，不因接收其文件而强加该 agent 依赖；用户可选择该包作独立顶层。browser/search 由 collector 的真实递归边带入，contact 不自建另一份同名配置。pdfx 普通库/CLI 为 runtime 依赖，不为它新注册 MCP。

上游 pin 统一按实际包身份：共享 agent-env 使用已支持所需字段的固定提交，base/vision 在 paper、collector、contact 中复用同一求值对象；仅在依赖 owner 已支持时使用 follows 或参数注入，不把不同构建上下文强行重写后假称原证据仍适用。同名不等价立即报冲突，不按安装顺序覆盖。collector、knowledge 的尚未存在 revision 是实施顺序前置，禁止填虚假 SHA 或手拷贝上游到 consumer；自有 runtime 可独立推进，完整 environment 待实际输出。

## 4. 资源、角色与固定入口

### 4.1 单源完整文件

从 `.apm/skills/professor-contact/` 完整复制（含隐藏辅助文件及 docs；不抽取 SKILL.md 充数）。保留现有 scripts/、docs/ 布局，在构建时私有 staging 固定必要入口的运行环境；不新增技能 bin/ 目录，不维护 Nix 专属业务副本。生成角色读取 `.apm/agents/` 的七个文件：professor-contact、downloader、idea-generator、selection、email-generator、email-validator、style-validator；analyzer 只取 `packages/professor-contact-codex/.apm/agents/`，不混入 OpenCode analyzer。

读取 YAML frontmatter 的 name/description，正文作 developer_instructions。源中 OpenCode model/temperature/permission 不照搬为 Codex 安全配置，也不发明映射；保留正文的读写/网络/非递归业务限制。未知需要的 Codex字段须交共享层 owner，不静默丢弃已批准功能。

`packages/professor-contact-codex/.apm/instructions/stage5-routing.instructions.md` 必须随技能资源复制，并将其原文作为 Codex 目标附录接入生成的 professor-contact SKILL.md 与 coordinator developer_instructions，让从 skill 或 coordinator 启动均可读到。不改它的顺序、spawn/wait、payload及失败规则，不假设复制一个未加载 instructions 文件就生效。不让这份 Codex 附录进入 APM/OpenCode 源。

### 4.2 安装位置与运行环境

保持原 `scripts/*.py`、相邻 imports 与资源位置。为实际被 skill/role 调用的七个自有脚本提供同目录、同 basename 的薄入口：`scripts/contact_targets`、`scripts/contact_stage1`、`scripts/contact_state`、`scripts/stage2_chatgpt_handoff`、`scripts/stage2_zotero_rpc`、`scripts/stage2_input_router`、`scripts/stage5_immutable`，各自调用同目录对应的 `.py` 原脚本。入口从自身位置解析相邻原脚本并原样传递 argv，保留 stdout、stderr 与退出码；不增加另一个命令族、子命令分派器或 bin/ 目录。`configure_opencode_depth.py` 只保留资源，不在 Codex 激活时运行。

在唯一源 skill/role 中仅把上述七个脚本的调用前缀调整为同目录薄入口，保留参数、scope、顺序与委派。源入口的非 Nix 后端沿用原 Python/uv；Nix 在 staging 固定该入口的解释器与直接程序路径。原 `.py` 接口继续保留，源角色正文原样生成，不在 Nix 副本改写业务命令或编排。只改 shebang 而仍执行 `python3 script.py` 不会固定解释器，不能作为替代。源入口匹配失败明确中止构建，不宽泛替换全部 python/uv 字样。

- router 的同目录薄入口在非 Nix 情况原样传递 loaded-skill 参数；Nix 情况把该 locator 绑定为锁定 Zotero 包已有 `${zoteroTools}/bin/zotero-item-export`，使用既有 `--exporter`，不与互斥的 `--zotero-read-skill-dir` 同传；显式 `--exporter` 保留原单 executable override 语义。只适配既有 locator/executable 选择，不处理业务输入。上游 store 包已有 bin 是其正式接口，不等于要求 contact 技能生成 bin。
- handoff 源适配点 `_run_future_work` 保留 R1 方案限定的可选 `CONTACT_PAPER_PYTHON` 单 executable：由 Nix 薄入口注入时，以 `[固定Python, script, *args]` 调用；未设置仍用 `[uv, run, script, *args]`。固定 Python 取 pdfcore `nix/pdfx.nix` 现有 `python` 返回值，不要求上游新加 public 属性。script 仍是安装后的 paper-analysis `scripts/future_work.py`，facts 仍同目录解析，所有验证/状态/错误/租约逻辑不改；不把 shell 串塞进 argv，不要求 0644 helper 可执行。
- Stage 5 immutable finalize：在唯一源 `professor-contact-email-generator.agent.md` 中，将 `skillrepo exec professor-contact .apm/skills/professor-contact/scripts/stage5_immutable.py stage5-finalize ...` 改为从当前已加载 `<professor-contact-skill-dir>` 定位并以参数数组启动 `<professor-contact-skill-dir>/scripts/stage5_immutable stage5-finalize ...`；不得依赖工作目录、`skillrepo` 注册表或开发 checkout。非 Nix 同名薄入口以原 Python 环境执行相邻的 `stage5_immutable.py`，Nix staging 中该入口绑定本包固定 Python；两种安装方式都保留原 `.py` 公共入口。`stage5_immutable.py` 的相邻 `contact_state.py` 定位、`sys.executable` 子进程及临时 provenance 副本必须沿用同一解释器，不改变 `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 已有解析、临时清理、错误传播或审计来源标签。保留来自同一教授 `owner_input_file` 的 `--program-root`、`--email-pack`、`--email-id`、`--mode`、`--result`、`--choices`、两个模板及可选 `--polish-mode` 的原值和 argv 传递；不得绕过 immutable wrapper 改为直接运行 `contact_state.py stage5-finalize`，也不得改动用户模板保护、邮箱核验、验证循环与实际写入行为。源调用锚点找不到时构建失败，不按文本相似性猜改。
- analyzer 直接调用 paper helper、pdfx、vision 时，Nix 使用已加载 paper-analysis 安装根的 `bin/future-work`、`bin/facts`、`bin/pdfx`、`bin/vision-glance`（固定版本的 `nix/paper-analysis.nix` 已公开）；Zotero session 使用已加载 zotero-read 安装根的 `scripts/new-session.sh`（上游 `nix/skill-resources.nix` 已固定其 bash/curl/coreutils）。不由 contact 再包装 `paper-helper`、`pdfx`、`vision-glance`、`zotero-session`。在唯一源中说明按已加载依赖的安装形态选择该 owner 的现有固定入口，非 Nix 保留原 `uv run`/既有入口；未来工作和 facts 始终来自同一 paper 安装。Nix 不改写这段源语义。Stage5 checker 仍从实际 sibling skill 解析，以自有固定 Python 运行，不从开发 checkout 兜底。
- KB 既有调用使用知识库 owner 的已安装固定 launcher，不由 contact 自建 KB server 或审批配置。

`runtimePackages` 只保留必要解释器和直接程序闭包，不提供隐式 PATH/PYTHONPATH。删除 R1 的 `bin/run-python`、`bin/run-tool` 统一改写要求：现有角色中的临时 JSON/date/shasum 等辅助命令保持原有调用，不为本次 Nix 交付新增通用运行器，也不承诺替 Codex 会话提供全局 shell 环境。由自有产品脚本实际启动的子进程，才在上述已定位入口按固定路径绑定真实直接依赖；实现若发现另一条必需调用仍缺固定运行环境，报告具体调用与最小适配，不把全部辅助命令重写作为默认任务。

### 4.3 安装与服务边界

只调用共享 `agent-env apply --project`，真实复制到 `.agents/skills` 和 `.codex/agents`；配置由其已验证保护机制处理。受管技能可完整升级替换，保留其他来源兄弟目录/无关配置/手改配置。等价复用不认领，同名含继承冲突不覆盖。无每仓安装器、无清根 rsync、无新 journal、无全局安全设置。

Zotero/Chrome/登录态/模型服务与 KB_SERVER_PATH 等真实服务仍由宿主按各 owner 文档提供，密钥不进 flake/store。安装不启动服务、发邮件或业务流程。离线 Stage0/候选构建不要求 Zotero；kb_import=false 不要求 KB服务在线。依赖包可安装但服务未测时如实标条件可用。现有 Codex角色中的委派方式照原源保留，只有实际调用错误才报告运行时限制，不额外修复历史迁移功能。

## 5. 实施顺序、影响与交接

1. 核 main 变化对本计划入口的影响，完成自有资源/runner固定层与 package定义；保留待交依赖接口，不伪造通过。
2. collector、knowledge producer给出上述实际可组合输出后固定提交，统一共享包身份，完成完整环境及 README。
3. 独立按P1–P4核此计划；执行实现及测试须取得对应批准。测试只按同目录测试计划 N1–N4 的安装/必要最小动作，不跑套磁全流程、共享安装器全回归或整仓旧测试。
4. README 分别标明固定输出、aarch64-darwin build证据、实际安装、角色最小调用、外部服务及未验证路径。只有完成的具体包/路径可称就绪。

R3 只补齐 Stage 5 `stage5_immutable.py` 的第七个固定入口及 email-generator 源调用前缀；沿用 R2 的同目录方案。N2 原有完整资源/角色安装核对涵盖此入口及其调用文本；N1–N4 目标、共享安装、其余资源/角色和业务边界不变，不新增完整邮件业务测试。R3 仍待独立计划复审，不因修订自授批准。

关键不变量：安装不改用户业务状态；原角色仅入口和载体变；资源从安装目录解析；Stage 5 始终经 immutable wrapper 进入原有同教授最终提交与模板保护路径；多根依赖不按顺序覆盖；helper与对应事实文件来自同一安装。代表性风险分别用固定wrapper、同版本对象、共享冲突处理、保留原同目录facts推导解决。源变动造成绑定失配就阻该构建，不能默认删掉安全/业务段落。

实施负责人为 contact producer；collector/knowledge缺的公开输出由各producer负责；MCP和配置保护由共享层负责。PR91/92合并后只分析受影响文件并更新pin，不因SHA变动自动重跑已成立的安装证据。此计划不授权合并、不声明方案已获审核通过。

