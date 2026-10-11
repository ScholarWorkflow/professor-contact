# 第 66 号正式运行尝试记录（2026-10-07）

## 依据与范围

本记录对应拉取请求 #73 的正式用例 `S3-RT-CODEX-1`，按已批准的测试计划 `issue-66-test-plan-r19-clarification-r7-2026-10-07` 执行。第十四版完整执行计划见评论 #6031810435，批准见 #6032336311；第二关口通过状态记在拉取请求正文中；R7 测试计划见评论 #6032362859。产品来源为提交 `fba6b1e3f2fe7aeb05d7855d9657a7f23a29b596`，夹具来源为提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`；运行配置为 `gpt-6-luna`、`low`、`workspace-write`。本记录只报告第三关口运行尝试，不改变已批准计划或产品代码。

## 结果

前十次启动尝试都在正式业务请求前停止；第十一次安装成功，按 R7 计划只发送了一次正式 `/eval` 请求。请求体预期和实际上传均为 640 字节，`curl` 返回码为 0，HTTP 状态为 200；请求证据记录 `attempt_number=1`、`maximum_attempts=1`。判定器最终给出 `INVALID_TEST_EXECUTION`：证据或输入来源无效，无法把观察到的业务事实归因到目标程序。因此 `S3-RT-CODEX-1` 没有业务通过或失败结论，也不会再次发送请求。

| 证据集 | 安装阶段结果 | 判定与说明 |
| --- | --- | --- |
| `issue66-formal-pr73-fba6b1e-20261007-01` | 安装退出码为 1。首次调用把仓库名写进了 `--product-source`；包装器又补了一次仓库名，形成重复来源选择器。 | `CASE_NOT_STARTED`。本地执行参数错误，不是产品行为结论。 |
| `issue66-formal-pr73-fba6b1e-20261007-02` | 来源选择器已修正；依赖仓库 `ScholarWorkflow/paper-analysis` 的 HTTPS 克隆因 TLS 连接提前结束而失败，安装事务未提交。 | `CASE_NOT_STARTED`。安装阶段网络失败，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-03` | 按用户指示重试。`verdict.json` 记录安装命令达到 1200 秒上限；隔离消费者目录留有部分安装文件。外层执行器当时返回码为 2，但该数值未保存到证据集，不能当作可复核的 APM 子进程退出码。 | `CASE_NOT_STARTED`。没有发出正式请求。该证据集缺少 `commands/014-install.json`、安装标准输出和标准错误，子进程返回码无法从证据集复核。 |
| `issue66-formal-pr73-fba6b1e-20261007-04` | 按用户指示继续尝试。APM 解析依赖后，克隆 `ScholarWorkflow/browser-pdf-tools` 时遇到 GitHub HTTPS TLS 连接提前结束；安装退出码为 1，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-05` | 安装运行 914 秒后，克隆 `ScholarWorkflow/knowledge-tools`、`ScholarWorkflow/base-skills` 和 `ScholarWorkflow/browser-pdf-tools` 时遇到 GitHub TLS EOF 与 `fetch-pack` 提前断开；安装退出码为 1，事务未提交。 | `CASE_NOT_STARTED`。原始安装输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-06` | 克隆 `ScholarWorkflow/pdf-processing-core` 时出现 TLS 提前 EOF；安装退出码为 1，约 25.2 秒后结束，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-07` | 克隆产品仓库 `ScholarWorkflow/professor-contact` 时出现 TLS 提前 EOF；安装退出码为 1，约 5.4 秒后结束，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-08` | 克隆 `ScholarWorkflow/knowledge-tools` 时出现 TLS 提前 EOF；安装退出码为 1，约 25.4 秒后结束，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-09` | 克隆 `ScholarWorkflow/knowledge-tools` 时出现 TLS 提前 EOF；安装退出码为 1，约 25.7 秒后结束，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-10` | 克隆 `ScholarWorkflow/zotero-tools` 时出现 TLS 提前 EOF；安装退出码为 1，约 25.5 秒后结束，事务未提交。 | `CASE_NOT_STARTED`。安装命令记录和输出已保存，没有发出正式请求。 |
| `issue66-formal-pr73-fba6b1e-20261007-11` | 安装退出码为 0。 | 已发出唯一一次正式请求，HTTP 200；最终判定 `INVALID_TEST_EXECUTION`。原始事件编号在 `24554–26700` 区间有 50 个缺号，判定器的序号完整性检查未通过；阶段三实际程序入口无法由观察到的命令输入证明；归因、凭据链、交接链、停止顺序和终态事实判定失败；原始产物、验证器写入范围和重建边界缺少可判证据。不能据此认定产品业务通过或失败。 |

第十一次判定中的事实项为：证据集、安装、夹具、运行前后快照、路由验证和阶段四产物缺席均为 `pass`；`F-entry-binding` 为 `invalid`；归因、凭据链、交接链、停止顺序和终态为 `fail`；原始产物、验证器写入范围和重建边界为 `gap`。这些是测试执行证据判定，不构成产品业务结论。

## 证据位置

前十份启动证据分别保留在 `/private/tmp/issue66-formal-pr73-fba6b1e-20261007-01` 至 `/private/tmp/issue66-formal-pr73-fba6b1e-20261007-10`，没有相互覆盖。第三份记录了超时和未发送请求的状态，但缺少安装命令 JSON 及原始输出；其余已执行到安装命令的证据集保留各自的命令记录和输出。

第十一次完整证据保留在 `/private/tmp/issue66-formal-pr73-fba6b1e-20261007-11`。传输结果见 `transport.json`，唯一请求及其上限见 `attempt.json`，安装记录见 `commands/014-install.json`，正式响应见 `response-raw.json`，判定及具体缺口见 `verdict.json` 和 `judge-verdict.json`，事件路由与快照核验见 `routing.json`。R7 的 `/eval` 最多发送一次的限制已达到；本轮到此停止，不重发、不重采样。
