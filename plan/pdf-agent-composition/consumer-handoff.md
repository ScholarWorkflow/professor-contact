# 公共 PDF 依赖接入交接

Revision: CONTACT-PDF-H1 (2026-10-22)
Status: draft / waiting for upstream; review pending; no implementation or test PASS claimed.

## 本 PR 当前内容

本次仅登记后续消费端接入边界，不修改 `flake.nix`、`flake.lock`、产品或测试代码。用户要求先创建四个 PR，先实施 pdf-processing-core 和 exam-question-pipeline 两个上游；本 PR 等待其输出，不预填尚不存在的 revision。

目标是 Contact 与 Study 作为两个顶层包交给共享 `mkProject` 后，递归收齐同一公共 PDF 包，并通过一次项目激活安装。不是串行运行两份独立 activate 脚本，也不是为两个产品新增特化安装器。

## 已核实基线与归属

- Contact: [`582f731caf438851bcec23662047daf1ed2098b9`](https://github.com/ScholarWorkflow/professor-contact/blob/582f731caf438851bcec23662047daf1ed2098b9/flake.nix)。`nix/contact.nix` 的 `agentDependencies` 直接引用 producer `pdfx-agent`，同时使用 producer 的 Python runtime。
- 当前公共 PDF: [`3444dca0e0b84f46d1839ab5c707afa78e23d3a7`](https://github.com/ScholarWorkflow/pdf-processing-core/blob/3444dca0e0b84f46d1839ab5c707afa78e23d3a7/nix/pdfx.nix)。公共 PDF 固定运行入口的修正属于该 producer。
- Exam 当前 [`d57c2c47ac5d3a4dc6579bbcfb2508352e696acd`](https://github.com/StudyCoachWorkflow/exam-question-pipeline/blob/d57c2c47ac5d3a4dc6579bbcfb2508352e696acd/nix/packages/pdf-adapted.nix) 改写同 id 的 PDF 内容；移除这份分叉属于 Exam，不在 Contact 重建第三份。
- 共享层既有包依赖组合与冲突检查继续有效；不以改名、强行覆盖或削弱冲突保护绕过不同 payload。

## 等待与接入边界

依赖项：[pdf-processing-core #11](https://github.com/ScholarWorkflow/pdf-processing-core/pull/11) 公共 PDF 统一，以及 [exam-question-pipeline #34](https://github.com/StudyCoachWorkflow/exam-question-pipeline/pull/34) 直接复用。两 PR 当前为计划阶段；最终消费 revision 与有效验证记录仍待交付，不能把计划提交当作可消费产品版本。

上游交付后，Contact 接入负责人重新读取当前主分支与上游实际文件，确认公开 `pdfx-agent` 和本仓现有 runtime 导入入口仍兼容，再仅更新必要的输入引用及相应 lock 节点。固定真实可消费 revision，并引用上游验证结果；不得把文档草案或 PR 合并状态当成已验证包输出。

保留 Contact 业务、APM/非 Nix 路径、七个既有入口、现有直接依赖与公开输出。不更新无关依赖，不改 paper/base/knowledge/Zotero，不夹带 agent-env-nix 符号链接功能升级。

若真实上游接口变更导致必须修改 Contact 产品行为，停止这一机械接入，说明具体影响并修订对应方案；不得在消费者补偿 producer 缺陷。

## 验证责任与完成条件

上游负责人交付公共 PDF 入口及 Exam 消费的有效结果。Contact 接入负责人核对本 PR 完整引用差异与受影响入口，复用未受影响结果，不追加 Contact 全业务回归或共享安装器全套回归。

两个消费者均接入实际验证版本后，由 Study 消费端 PR 的执行负责人统一完成 Contact + Study 双根项目的必要组合安装验证，将实际版本、平台和结果写入 Study 的 `plan/pdf-agent-composition/consumer-handoff.md`；Contact 只链接同一结果，不在两仓分别重跑。范围限组合成功、唯一公共 PDF 实例及资源实际复制，具体步骤待在 Exam 本次正式测试计划补齐后沿用，不另建测试关口或判定器。

当前没有执行本次组合验证。仅在最终 diff 确实为有界引用调整且已有证据足够时，才由独立审核者判断快路径适用与合并条件；本文件不授予 APPROVED、PASS 或合并许可。
