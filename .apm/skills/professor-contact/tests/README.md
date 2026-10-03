# 测试目录使用说明

本目录是 professor-contact 的生产者测试区。这里的工具只用于测试，只使用虚构数据；不读取真实用户资料，不启动浏览器、外部服务或代理，不修改业务程序。

## 职责分工

| 职责 | 位置 | 说明 |
| --- | --- | --- |
| 共用准备工具 | `tests/runtime/fixture_support.py` | 目录检查、文本/JSON 写入、文件摘要；不含业务数据和业务断言 |
| 问题专属准备入口 | `tests/runtime/prepare_issue*_fixture.py` | 生成该议题的业务样例和清单；业务数据由入口自己定义 |
| 既有请求构造与验证入口 | `tests/runtime/build_issue*_eval_request.py`、`tests/runtime/verify_issue*.py` | 各自议题的命令构造与运行后判定，不在本次共用范围内 |
| 结构化执行与判定 | `tests/gate2_evidence.py` | 运行 unittest 并按执行阶段分类结果，产出 JSON 证据 |
| 问题专属业务样例和断言 | `tests/test_*.py` | 每个议题的业务验收断言由对应测试负责 |

## 共用准备工具：fixture_support.py

`fixture_support.py` 提供四类能力：

1. **目录检查**：样例根目录和清单输出拒绝生产者检出目录及其子目录；样例根目录拒绝非目录目标和已有内容的目标；第 53 号的程序根与资料根必须相互独立，不得相等或互为祖先。
2. **目录准备**：已存在的空目录保持原样；缺失目录由准备工具创建。准备结果记录该目录是否由本次调用创建，以及准备时的文件系统身份，供第 53 号失败回滚时判断能否安全删除。
3. **写入**：`write_json` 保持既有字节格式（`ensure_ascii=False`、`indent=1`、结尾换行）；清单输出使用排他创建，已有文件一律拒绝，不覆盖。
4. **摘要**：`file_sha256` 按文件字节计算 SHA-256。

冲突和拒绝统一通过 `FixtureBuildError` 报告。预先发现的冲突在任何样例写入之前失败；清单创建时若目标已经出现，则拒绝覆盖。本次已经写出的部分样例保留用于诊断，不自动重试、不递归清理。

## 目录分配

每次测试运行由调用方分配独立的可写目录。项目测试规则要求不同运行使用独立目录；通常由临时目录工具生成带随机后缀的目录，例如 `/tmp/issue74.vyhmHAsr`。共用准备工具只检查和准备本次收到的目录，不负责协调不同运行之间的目录分配。

## 调用既有准备入口

两个既有入口保持两种受支持的调用方式，调用方不需要修改运行目录，也不需要额外设置模块搜索路径：

```bash
python -B tests/runtime/prepare_issue55_stage3_fixture.py \
  --program-root /tmp/pc55/program --output /tmp/pc55/setup.json
```

```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "issue55_fixture", "tests/runtime/prepare_issue55_stage3_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
manifest = fixture.build_fixture(program_root, output=setup_json)
```

入口失败时打印 `{"status": "error", ...}` 并返回退出码 1；成功时打印 `{"status": "ok", ...}` 并返回退出码 0。清单字段、生成文件字节与摘要与迁移前保持一致。

## 执行测试与判定结果

完整回归继续使用既有结构化判定入口：

```bash
python tests/gate2_evidence.py \
  --start tests --pattern 'test_*.py' --out /tmp/pc-evidence.json
```

判定入口按 unittest 的执行阶段区分结果：`FAIL` 表示产品断言失败，`INVALID_TEST_EXECUTION` 表示准备或环境问题，`PASS` 表示全部通过。产品断言失败不能当成准备失败处理；空执行不能当成通过。

## 新增议题专属样例

1. 新建 `tests/runtime/prepare_issue<编号>_fixture.py`，从 `fixture_support.py` 复用目录检查、写入和摘要能力。
2. 业务数据、清单字段、`forbidden_outputs` 由入口自己定义；清单输出路径必须是不存在的新文件。
3. 入口须继续支持直接执行，以及测试按文件路径加载模块。
4. 问题专属业务断言写在 `tests/test_issue<编号>_*.py`，复用 `gate2_evidence.py` 的结构化结果做验收。
