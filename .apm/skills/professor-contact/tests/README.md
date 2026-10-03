# 测试目录使用说明

本目录是 professor-contact 的生产者测试区。本文说明四类职责的分工：共用准备工具、既有执行与判定入口、问题专属样例与断言、以及如何新增样例。所有工具只承载测试用途，只用虚构数据；不读取真实用户资料，不启动浏览器、外部服务或代理，不修改业务程序。

## 职责分工

| 职责 | 位置 | 说明 |
| --- | --- | --- |
| 共用准备工具 | `tests/runtime/fixture_support.py` | 目录保护、独占占用、文本/JSON 写入、文件摘要；不含业务数据和业务断言 |
| 问题专属准备入口 | `tests/runtime/prepare_issue*_fixture.py` | 生成该议题的业务样例和清单；业务数据由入口自己定义 |
| 既有请求构造与验证入口 | `tests/runtime/build_issue*_eval_request.py`、`tests/runtime/verify_issue*.py` | 各自议题的命令构造与运行后判定，不在本次共用范围内 |
| 结构化执行与判定 | `tests/gate2_evidence.py` | 运行 unittest 并按执行阶段分类结果，产出 JSON 证据 |
| 问题专属业务样例和断言 | `tests/test_*.py` | 每个议题的业务验收断言由对应测试负责 |

## 共用准备工具：fixture_support.py

`fixture_support.py` 提供五个能力，供各准备入口复用：

1. **路径保护**：样例根目录和清单输出都拒绝生产者检出目录及其子目录；样例根目录拒绝非目录目标和已有内容的目标；两个样例根目录（如第 53 号的程序根与资料根）必须相互独立，不得相等或互为祖先。
2. **独占占用**：目录身份是解析后的完整路径。准备开始前在样例根目录旁用排他创建取得一个占用目录，保持到本次写入完成或回滚结束；相同真实路径的并发准备会竞争同一个占用，遇到已有占用立即失败，不接管、不删除。占用名称编码属于共用模块内部实现：把一个真实存在的占用命名目录本身用作样例根目录或清单输出，会在任何占用取得或写入发生前被拒绝；仅名称形状相同但不存在占用目录的路径，以及占用形目录内部的路径，仍是合法输入。占用目录本身及其内部不进入样例内容或清单输出。
3. **目录准备**：已存在的空目录保持原样并记录归属（调用前已存在还是本次创建）；不再删除后重建。归属信息随成功结果交还调用方内部使用。
4. **写入**：`write_json` 保持既有字节格式（`ensure_ascii=False`、`indent=1`、结尾换行）；清单输出使用排他创建，已有文件一律拒绝，不覆盖。
5. **摘要**：`file_sha256` 按文件字节计算 SHA-256。

冲突和拒绝统一通过 `FixtureBuildError` 报告；写入过程中的意外错误按原异常通道向上传递。预先发现的冲突在任何样例写入之前失败，不留下副作用；检查之后出现的清单创建冲突由排他创建拒绝，本次已写出的部分样例保留用于诊断，不自动重试、不递归清理。

## 目录分配与异常清理

每次运行使用自己独立的样例目录（通常在系统临时目录下），不同真实路径的运行不共享可写状态。占用目录位于测试隔离空间（样例根目录旁），不进入样例内容或清单。

进程异常终止可能遗留占用目录和部分样例。后续运行遇到遗留占用会拒绝并报告，不自动判断陈旧、不自动删除；此时应换一个新的隔离目录重新运行。整个隔离空间的定期清理由运行测试的人负责，共用工具不做全局清理。

## 调用既有准备入口

两个既有入口保持两种受支持的调用方式，调用方不需要修改运行目录，也不需要额外设置模块搜索路径：

```bash
# 方式一：直接执行脚本
python -B tests/runtime/prepare_issue55_stage3_fixture.py \
  --program-root /tmp/pc55/program --output /tmp/pc55/setup.json
```

```python
# 方式二：测试内按文件路径加载模块
import importlib.util

spec = importlib.util.spec_from_file_location(
    "issue55_fixture", "tests/runtime/prepare_issue55_stage3_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
manifest = fixture.build_fixture(program_root, output=setup_json)
```

入口失败时打印 `{"status": "error", ...}` 并返回退出码 1；成功时打印 `{"status": "ok", ...}` 并返回退出码 0。清单字段、生成文件字节与摘要与迁移前保持一致。

## 执行测试与判定结果

完整回归使用既有结构化判定入口，把证据保存为 JSON 并按字段判断：

```bash
python tests/gate2_evidence.py \
  --start tests --pattern 'test_*.py' --out /tmp/pc-evidence.json
```

判定入口按 unittest 的执行阶段区分结果：`FAIL` 表示产品断言失败，`INVALID_TEST_EXECUTION` 表示准备或环境问题，`PASS` 表示全部通过。两条红线：产品断言失败不能当成准备失败处理；空执行（没有运行任何测试）不能当成通过。

## 新增议题专属样例

为新的议题添加准备程序时：

1. 新建 `tests/runtime/prepare_issue<编号>_fixture.py`，从 `fixture_support.py` 引入路径保护、独占占用、写入和摘要能力，不要重复实现这些操作。
2. 业务数据、清单字段、`forbidden_outputs` 由入口自己定义；生成文件与清单通过共用写入函数落盘，清单输出路径必须是不存在的新文件。
3. 按上面两种方式之一保证入口可被直接执行，也可被测试按路径加载。
4. 问题专属业务断言写在 `tests/test_issue<编号>_*.py`，复用 `gate2_evidence.py` 的结构化结果做验收；断言失败分类为产品失败，不得伪装成准备失败。
