# PR #134 本地测试执行记录（2026-10-23）

## 角色、版本与范围

- 执行角色：本地执行工程师；任务为跑完 PR #134 剩余测试并推送记录。
- 被测产品：`13f4eacb42f49e3e50d73e4f3ae5779609727194`；基线：`ad16b21c46978087329e94843e7b549515cf3274`。后续仅增加本记录，不改变被测产品。
- 产品范围以 [PR #134](https://github.com/ScholarWorkflow/professor-contact/pull/134) 为准：六个直接输入改用对应分支作为更新来源；只有 paper-analysis 的实际锁定提交更新为 `c140658cc60f9d9c3d17008cbab0b599f40c8e46`；其余锁定值及依赖关系保留。agent-env-nix 与 nixpkgs 不变。
- 本次沿用 [缓存激活测试计划 t4](../cached-nix-activation/test-plan.md) 的固定版本 Darwin 构建与一次 README 隔离安装步骤，只将产品 SHA 替换为本 PR 的产品版本。构建已包含求值，不另设独立 drvPath 测试。
- 原 [PDF 消费交接 H2](../pdf-agent-composition/consumer-handoff.md) 归属 Study PR16 的组合验收仍由原负责人承担，本次不重复执行该组合验收。
- 不改变产品、测试断言、锁文件或运行配置；不新增业务回归、模型调用、外部服务操作或平台矩阵。

## 环境与原始记录

- 平台：Darwin arm64；Nix 2.34.8；direnv 2.37.1；jq 1.8.2。复用已有安装及不可变缓存。
- 仓库外运行目录：`/tmp/contact134.DIqjYh`；新消费者：该目录下的 `consumer/`。
- 原始记录：`build.sh`、`build.log`、`build.exit`、`executable.exit`、`activate.sh`、`lock.log`、`lock.exit`、`consumer-contact-rev.txt`、`direnv-allow.log`、`direnv-allow.exit`、`activation.log`、`activation.exit`。这些文件不入库。
- 保留原 HOME 和现有 Nix/direnv 配置；`XDG_DATA_HOME` 仅指向本运行目录内的 `direnv-data/`。未操作用户项目或业务数据。

## 逐项结果

| 项目 | 结果 | 依据 |
| --- | --- | --- |
| 分支来源、定向锁定更新、其余锁定值与依赖关系保留 | 通过（复用） | PR 原有两阶段结构检查、语法检查、离线 metadata 与 lock 一致性记录；本轮产品未修改，不重复执行。 |
| 固定版本 Darwin 实际构建 | 通过（本次执行） | 下述构建退出 0，激活入口可执行检查退出 0。 |
| 固定版本消费者锁定 | 通过（本次执行） | `nix flake lock` 退出 0；`jq` 读取的实际 contact 提交与被测 SHA 相同。 |
| 一次 README 隔离安装 | 通过（本次执行） | `direnv allow` 与 `direnv exec` 均退出 0；成功标记和安装后的技能文件同时存在。 |
| 当前产品 CI | 通过（复用自动运行） | GitHub 返回当前产品提交的 [CI 39944716132](https://github.com/ScholarWorkflow/professor-contact/actions/runs/39944716132) 已完成且结论为 `success`。此结果不替代 Darwin 构建与安装。 |

### Darwin 构建

```sh
CONTACT_SHA=13f4eacb42f49e3e50d73e4f3ae5779609727194
CONTACT_REF="github:ScholarWorkflow/professor-contact/$CONTACT_SHA"
RUN=/tmp/contact134.DIqjYh
nix build "$CONTACT_REF#professor-contact-activate" --out-link "$RUN/activate"
test -x "$RUN/activate/bin/professor-contact-activate"
```

两条命令均退出 0。2026-10-23 19:45:29 开始、19:46:03 结束（北京时间），约 34 秒。实际输出为 `/nix/store/ngzni35cn3510akh4w4rvr00acrf2626-professor-contact-activate`。构建包含真实 paper-analysis 包、Contact 包、完整环境和激活入口；未替换依赖或使用本地路径输入。

### README 消费者安装

消费者 `flake.nix` 使用 README 中的 `contact` 输入、`nixpkgs.follows = "contact/nixpkgs"` 和 `mkShell` 示例；保留 `shellHook` 中的 `--project "$PWD"`。实际命令：

```sh
cd "$RUN/consumer"
nix flake lock --override-input contact "$CONTACT_REF"
jq -er --arg sha "$CONTACT_SHA" '.nodes.contact.locked.rev | select(. == $sha)' flake.lock
printf '%s\n' 'use flake' > .envrc
export XDG_DATA_HOME="$RUN/direnv-data"
direnv allow .
direnv exec . sh -c 'test -f .agent-env-applied && test -f .agents/skills/professor-contact/SKILL.md'
```

以上命令均退出 0。实际 contact 锁定提交为 `13f4eacb42f49e3e50d73e4f3ae5779609727194`。安装于北京时间 19:46:42 开始、19:47:02 结束，约 20 秒；日志记录真实安装器的 `agent-env: apply completed.`。

- `.agent-env-applied` 已生成，内容为 `v1`、环境 `/nix/store/v1590kljl0zpdi0pbypaay8vd32ibsyr-professor-contact-environment`、消费者物理路径 `/private/tmp/contact134.DIqjYh/consumer`，共 117 字节。
- `.agents/skills/professor-contact/SKILL.md` 已安装，177281 字节。
- 每个构建及安装步骤各执行一次，无失败、无重试；此前云端获取 agent-env-nix 归档的 HTTP 404 记录保留为历史事实，本机没有复现该阻断。

## 交付与边界

本次剩余 Darwin 构建和隔离安装已完成，没有发现需要修复的产品问题；仅提交测试执行记录。未执行 Study PR16 的组合验收、上游原生代理业务测试或完整 Contact 业务回归。上述未执行项目不属于本轮剩余测试。

本记录报告实际结果，不自行授予测试关口通过或 merge 批准。下一步由相应审核负责人核对本 PR 的实现与结果。
