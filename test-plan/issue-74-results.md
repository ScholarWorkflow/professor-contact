# 第 74 号议题正式测试结果

## 当前状态

- 测试方案：`issue74-plan4-test-r1`。
- 本文件当前为结果记录载体；最终 Gate 3 结论将在包含本文件的当前 HEAD 完成正式执行后填写。
- 已保留的前一正式执行：产品 `22a4db04fb56979d0c1c5897f12ae1276746b427`，GitHub Actions run `37143207242`，CPython 3.12.14，`jq` 1.7。
- 该次执行六个 Case 均为 `PASS`，退出码均为 0，独立检出保持干净；完整结构化证据保存在 workflow artifact `issue74-formal-22a4db04fb56979d0c1c5897f12ae1276746b427`。
- 因本结果文件随后加入 PR 差异，当前 HEAD 仍需按冻结 Recipe 再执行一次 `T74-STATIC` 所在的完整六 Case 组合，不能把前一提交的 PASS 直接写成最终 Gate 3。

## 前一执行摘要

| Case | tests_run | verdict | failures | errors | skipped | missing required prefix |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| T74-CORE | 16 | PASS | 0 | 0 | 0 | 0 |
| T74-CLI | 3 | PASS | 0 | 0 | 0 | 0 |
| T74-53 | 8 | PASS | 0 | 0 | 0 | 0 |
| T74-55 | 16 | PASS | 0 | 0 | 0 | 0 |
| T74-STATIC | 4 | PASS | 0 | 0 | 0 | 0 |
| T74-EVIDENCE | 4 | PASS | 0 | 0 | 0 | 0 |

前一执行中 `load_errors=[]`、`events=[]`、`interruption=null`，六个 Case 的 `started` 与 `completed` 一致；`T74-CLI` 的兼容基准逐字节比较实际执行且未跳过。

## 最终执行

待当前 HEAD 的正式执行完成后更新；本节内容不得预先填入 PASS。
