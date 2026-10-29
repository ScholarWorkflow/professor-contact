# Stage 5 邮件中文译文测试计划

- Test plan revision: TP1.1（仅补齐 T3 无译文断言）
- Requirement/implementation: [R1](implementation-plan.md)
- Baseline: `ad096fe31a4b5694cbe47a40f37b621435e1eeec`
- 独立 review：TP1 Gate 1 PASS；TP1.1 的 T3 Gate 2 已独立确认 PASS，T1–T2 Gate 2 沿用；T4 环境步骤仍待补。来源见 [review-record.md](review-record.md)。执行结果：未执行；作者不自授 PASS。

## 必测清单（范围上限）
|目标|输入/场景|预期/检查入口|
|---|---|---|
|T1 双邮件正常渲染与发送隔离|现有合成教授 fixture，mode both，最终动态字段/choices，与两个 translation_source 对应中文 subject/body|当前 unittest 框架检查两个 md 正文后分别包含正确译文；两个 txt 精确等于各自 translation_source、无中文附节；模板字节不变；原日文长度/兴趣校验不把译文当输入。|
|T2 翻译失配/缺失拒绝和手改保护|同一 fixture 已生成输出后给出 stale source_text，及完整文件缺本次跟进行；合法译文输入遇现有手改 md|既有 CLI 返回明确失败/needs_decision，既有 md/txt/state 字节不变。只检查这三个实际改变/依赖的失败行为，不做类型/排列穷举。|
|T3 旧直接CLI兼容|现有 immutable 无 translations 调用|保持成功、模板固定文本不变、无译文；复用现有 `test_finalize_without_full_body_humanizer_preserves_fixed_segments`，同 case 增加 `assertNotIn("## 中文译文", md)`，显式确认省略参数时无译文节。|
|T4 模型生成译文忠实且 validator 边界正确|一次正常 Stage 5 mode both 小样例，已验证资料与选择，实际 generator 及 validator|查看首封/跟进最终 md/txt：中译完整覆盖最终 Subject+正文，否定/日期/事实/请求强度不变；无新事实；译文不发送；validator 不将中文计入日文长度/三句规则，不漏掉明显翻译缺陷。仅一次，不重跑上游业务。|

## Gate 2 可执行步骤
### T1–T3 云端离线
- 使用仓库现有 Python unittest 与 `.apm/skills/professor-contact/tests/test_stage5_immutable.py` 的 `BaseEnv/prepare/write_inputs/run_wrapper`，仅新增本功能用例；不新建测试框架或判定器。
- fixture 以 tempfile 创建独立 `/tmp` 状态，现有 contact-evidence stub 仅供离线 runner 检查，不声称真实外部服务/模型成功。不访问用户文件、Mac或生产配置。
- 在仓库根执行：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage5_email_translation.py' -v`（T1/T2）；T3 执行 `cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_immutable.TestStage5ImmutableTemplates.test_finalize_without_full_body_humanizer_preserves_fixed_segments -v`。
- 日志放仓库外 `/tmp/stage5-email-translation-validation/`，记录产品 SHA/工作 diff、命令、exit/status/必要输出；不提交原始用户材料。
- 失败先保留输出并诊断；产品缺陷修复后仅重跑受影响项，不改变期望求通过，不跑全仓回归。

### T4 正式模型观察（待可用执行环境）
- 必须使用已有隔离 consumer 和已安装当前精确版本，既有 eval 服务/业务 fixture，不从本生产仓库调用模型，也不启动 eval 服务、不碰 Mac。
- 当前云端尚无已确认的 consumer/eval/fixture 路径，故 T4 **未执行、步骤尚不可执行**，Gate 2 此项待补；不把猜测的安装命令或模拟翻译记成真实通过。
- 可用环境提供者交付现有 consumer 路径、eval 调用 recipe、已验证 Stage 5 小样例和该次输出目录后，仅补齐一次 mode both 调用与实际观察路径，由独立 reviewer 复核 T4 Gate 2；不重开 T1–T3、不新增上游全流程/重复安装要求。
- 若用户最后决定自己在 Mac 测试，云端交接当前 Draft PR 与目标清单，不自动接管其环境。

## 记录与结束
结果分通过/业务失败/无法判断/未执行；T1–T3 离线机械结果不能替代 T4 翻译语义及实际模型接线。未完成 T4 不宣称整体通过或可合并。仅更新本目录简短执行记录；独立 reviewer 给正式 Gate 结论。
