# PR148：三部分兴趣段测试计划与已有结果

- Test plan revision: TP1，2026-10-27；对应 [EP1](execution-plan.md)。
- 产品/测试版本: `4ea37fa6cb09b5a5bd4df8925a438d98a5f96d72`，base `901fb109701bea61a62239f95c9da865fafb1e4e`。
- 本轮仅整理与审核既有检查，不声称以下运行是在计划批准后重新执行。设计、Gate1–3的实际结论见 [review.md](review.md)，作者不自授PASS。

## 唯一必测范围

| 目标 | 输入 / 场景 | 预期 | 现有检查与证据 |
| --- | --- | --- | --- |
| T1 自然首句指导接入与合法三项正常输出 | 原有隔离合成夹具，经正式wrapper plan→finalize | job为3项且含已确认首句指令；输出全部三项及future，无固定④及④来源行 | `test_stage5_immutable.TestStage5ImmutableTemplates.test_three_part_interest_plan_and_render`；并人工读完整opening、SKILL及generator引用，确认未固定句型/虚构事实、②③future不变 |
| T2 旧四项拒绝且保护已有文件 | 先有合法邮件，再提交附加④的旧结果 | 非零退出、数量错误，原md/txt/状态字节不变 | `test_stage5_immutable.TestStage5ImmutableTemplates.test_legacy_four_part_result_is_rejected_without_rewriting_existing_email` |
| T3 遗留来源映射拒绝及原限制保持 | 3项结果附④source_map；正常现有模板/用户选择夹具 | 明确拒绝④；180/200常量保留；模板/用户选择既有保护不变 | `test_stage5_immutable.TestStage5ImmutableTemplates.test_retired_source_row_is_not_silently_accepted` 与下述已执行Stage5集合；代码静态核对其余校验无改动 |

三个新增方法所在模块：[test_stage5_immutable.py](https://github.com/ScholarWorkflow/professor-contact/blob/4ea37fa6cb09b5a5bd4df8925a438d98a5f96d72/.apm/skills/professor-contact/tests/test_stage5_immutable.py)。不增加边界组合、安装、业务全链、模型自然度eval、浏览器或MCP测试，不新建判定器。

## 已有运行与复用

2026-10-27云端隔离工作区执行过以下命令（Python unittest，无安装/外部服务，合成夹具使用临时目录，不连接用户状态）：

```sh
cd /workspace/shared/contact-email-natural/.apm/skills/professor-contact/tests
python -m unittest test_stage5_immutable test_stage5_dualtarget_contract test_stage5_template_body test_contact_state.TestStage5 -v
```

实际结果：`Ran 53 tests in 22.383s`、`OK`，原日志 `/tmp/contact-three-regression.log`。执行对象是base901fb109上候选工作树；后来PR148的10个修改文件blob与该受测候选逐一一致，产品/测试内容没有变化，故请求本轮Gate3确认复用，而非把旧运行改写为新SHA上重跑。此前新增测试初次运行曾使用错误job键`expected_output`而失败，修正为实际`result_schema`后上述53项重跑成功；不将首次失败隐去或视为产品故障。

当前固定产品SHA的仓库CI：[run40502317649](https://github.com/ScholarWorkflow/professor-contact/actions/runs/40502317649)，四个shard及汇总`test`均success。CI执行既有分片集合，不将全仓CI扩为本计划新增必测清单。[issue74-formal](https://github.com/ScholarWorkflow/professor-contact/actions/runs/40502317592)为skipped，不计PASS。PR作者另列的13/90/38/3项结果仅作其说明，本计划不依赖其未取得的本地原始日志。

## 准备、检查方式与失败处理

当前无需新准备/安装/执行，reviewer直接读现有源码、上述日志摘要及固定CI结果，按T1–T3检查覆盖和适用性。完整合成用例及准备由既有test模块自带；若将来真实修改使复用失效，由测试负责人先明确受影响目标，再在隔离源码工作区用相同模块入口按需执行，输出保存在新的`/tmp`目录，不覆盖旧记录。不得因为文档提交或记录格式变化重跑，也不为取得PASS调整预期。

人工静态核对：完整首句规则是否忠实于用户决定、三项合同贯通生成/校验/渲染、②③future及180/200未改、旧结果失败在文件写入前。此检查不等于模型实际文风效果已验证。

不足/异常按事实分类：已有产品失败交实现负责人；命令/环境无法运行记无法判断；确缺已有记录先请求，不自动补测。只复审受影响目标，禁止新增来源认证、过程证明及测试矩阵。此文档提交后若CI按仓库设置自然触发，观察到终态即可；不手动重跑。
