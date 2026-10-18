# professor-contact Nix 测试计划

- Test plan revision: TP5.1（恢复已确认的 `--sandbox workspace-write --cd` 调用并删除预先信任门槛；此变更已由 [6247386156](https://github.com/ScholarWorkflow/professor-contact/pull/93#issuecomment-6247386156) 定向复核，N1–N4 不变；TP5 原修订：2026-10-18；按 PR #93 第二关口审核意见补齐 N3 的 PDF 样本准备步骤，N1–N4 目标、预期与检查方式不变，沿用 TP4 的安装态命令、N4.1 selection 准备与判定链、N4.2 PR90 复用命令与本机有限预检），关联 [执行计划 R3](implementation-plan.md)。
- Review status: Gate1/Gate2 已由 [6247386156](https://github.com/ScholarWorkflow/professor-contact/pull/93#issuecomment-6247386156) 确认通过；产品 `5032a28882a36789a8b0c81e8c25ed6233f8abd0` 已补入 collector，aarch64-darwin 完整 N1/N2 结果已提交，N3/N4 沿用未受影响记录，见 [执行记录第 9 节](test-execution-2026-10-18.md#9-collector-接线与-n1n2-复核2026-10-18)。Gate3 待审核上述新结果与复用依据；本次仅同步事实，不自授结果通过。
- 产品基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`；执行时记录真正待验实现SHA与锁定依赖。只验本次 aarch64-darwin / Codex 安装和必要入口，不扩 Stage0–5 业务回归。
- 历史 TP5 测试准备时点（本地测试工程师）交付：N3 的 PDF 样本生成与 papers.json 命令（第二关口唯一待修项）、TP4 已有的 N3 命令与新增断言、N4.1 与 N4.2 的可直接执行准备及判定命令、仓库外预检记录。未修改产品代码，未构建、未安装、未运行任何正式用例。

## 1. 必测清单（上限）

| ID | 目标/输入 | 预期 | 检查方式 |
|---|---|---|---|
| N1 | 固定提交的 runtime、完整 agent、environment | Darwin实际build；完整包由真实依赖组成，默认codex且包级可override | nix build实际结果；读结构化agent-env元数据，override求值不另建安装矩阵 |
| N2 | 一个仓库外新consumer实际apply，含无关sentinel技能 | 完整skill/scripts/docs/8个角色/Stage5附录；必要依赖和MCP正确归属，sentinel保留 | 文件与source静态比对、TOML/JSON解析；共同源入口适配以外正文无业务改写。共享冲突/删除/继承/回滚测试引用原共享证据，不重跑 |
| N3 | 从安装scripts薄入口执行小型preview正常输入及router已有PDF；handoff helper固定调用 | runner实际产生预期业务JSON，资源/同目录import可达；helper使用固定环境及同一paper安装，原uv默认非Nix路径保留 | 下述本地最小动作+完整diff检查。handoff受影响的既有确定性测试按原fixture复用，只选_run_future_work/facts locator相关测试，不跑完整ZIP/模型流程 |
| N4 | 安装角色一次真实Codex调用；router一次真实Zotero摘要导出 | named角色可用且遵守原输入边界；缺PDF记录得到规范化JSON，非FileNotFoundError | 原生调用返回业务结果；按PR90真实摘要recipe复用服务准备，消费实际导出文件。不把help或mock当完成 |

这些目标来自Nix共识最小验收。N3不要求新建判定器、无异常组合穷举。N4不下载论文、不调用OCR模型、不导入KB、不发邮件；collector/browser/KB未变服务行为及共享MCP结果直接复用有效上游记录。若固定入口改动影响某个上游结果，明确那一入口后补相应最小动作，不自动增加完整服务矩阵。

## 2. 环境、准备与复用

由本地执行者使用 aarch64-darwin Nix+既有Codex eval服务。此文不授权现在安装/运行。执行者从获审实现提交确定 `CONTACT_REF=github:ScholarWorkflow/professor-contact/<实际40位SHA>`，把它记入结果；不能拿无产品实现的纯计划SHA构建，不能使用path input、手拷贝技能或开发checkout修补consumer。

准备单个仓库外临时目录，例如 `RUN=$(mktemp -d /tmp/contact-nix.XXXXXX)`；consumer=`$RUN/consumer`，业务样本=`$RUN/data`，输出=`$RUN/output`；分别mkdir。保持现有HOME，不抹掉Nix认证；必要时独立CODEX_HOME，使用既有eval配置/账号，不读eval自身配置查信任列表。测试服务如需Zotero必须使用已授权的独立测试库和loopback端点，不能读取生产库。缺平台、collector/knowledge实际包、服务/模型配置就标对应项未执行/无法判断，其余独立项继续。

只N2要求一次新安装；后续全部用同一个有效consumer。文档更新不重装；重试仅重置本项可变样本，不清用户目录或全局缓存。

本轮补入的固定输入：

- 共享夹具固定为 `skills-test-fixtures@8cecafc694e4591dee47372f38903e5ac2b689fe`，与 [PR90 recipe](../pr90-macos-real-abstract-export-recipe.md) 同一 pin；按该 recipe 第 2 节取得该 pin 的检出（已有同 rev 且干净的检出可直接复用，否则 clone 到 `$RUN` 后 `checkout --detach`），执行时断言 `git rev-parse HEAD` 等于该 pin。该提交已确认含 `configs/codex-consumer.toml`、`configs/codex-nested-delegation-consumer.toml`、`configs/codex-eval-adapter-contract.json`（`skills-test-fixtures/codex-eval-adapter@19`）、`scripts/prepare_shared_test_assets_macos.sh`、`scripts/start_zotero_test_fixture_macos.sh`、`scripts/parse_codex_eval_evidence.py`。
- 消费者 Codex 配置只有一个来源：把该 pin 的 `configs/codex-nested-delegation-consumer.toml` 合并进 `$RUN/consumer/.codex/config.toml`（保留其中的 `model="gpt-6-luna"`、`model_reasoning_effort="low"`、`sandbox_mode="workspace-write"` 与 `[features.multi_agent_v2] enabled=true`，并保留安装生成的其它设置）。eval 请求按用户已确认的方法显式传入 `--sandbox workspace-write --cd <consumer>`；模型、推理及委派开关继续复用上述项目配置，不追加模型、trust 或 MCP 环境覆盖，也不使用 `--ephemeral`。不将夹具说明中的 CLI 限制恢复为本轮新增门槛。
- 不要求 consumer 预先登记信任或提供信任证明，不读取 eval 自身配置查询信任名单，不修改服务、HOME/CODEX_HOME、认证或全局安全设置。`--cd` 使用下文 resolve 得到的规范化 consumer 路径。按上述已确认请求执行后，若项目配置或已安装角色实际未加载，依据原始响应记录具体事实与阻塞/无法判断；不预先以信任状态阻止 N4.1。
- 2026-10-17 本机有限预检（只确认命令与输入可用，未调用任何被测入口、产品入口或业务请求）：`nix (Nix) 2.34.8`；`nix eval --impure --raw --expr builtins.currentSystem` = `aarch64-darwin`；`python3 3.14.7`；`jq 1.8.2`；`yq v4.54.1`；`uv 0.12.22`；`git 2.55.0`；在既有 eval-server 检出目录内执行 `direnv exec . printenv EVAL_PORT` 返回 `17902`（该目录自身没有 `.envrc`，`EVAL_PORT` 由其上级 `.envrc` 提供，`HARNESS_WORKSPACE` 取该检出目录）；`/Applications/Zotero.app` 存在；夹具 pin 在本地仓库可解析。记录保存在仓库外 `/tmp/pr93-te-precheck/`（`tools.txt`、`eval-port.txt`、`zotero-app.txt`、`fixtures.txt`）。
- 当前接线基准：research `6e46f2961ba213c896b536bbbaa7de838b1070d4` 的 `packages.aarch64-darwin.professor-collector` 已存在并有 T1/T2 结果；knowledge `bdb0db128b7cfccc6a3b20a8d0acee8695d0e211` 工厂已接入。contact 产品 `5032a28882a36789a8b0c81e8c25ed6233f8abd0` 已补入 collector 直接边及真实递归闭包，不再等待 producer 或产品接线。
- collector/contact-evidence 及其递归闭包已接入；受影响 N1/N2 的实际构建、完整安装与 MCP 归属结果已提交，N3/N4 未受影响结果按执行记录第 9 节复用。下一步只审核这些结果与复用依据，不增加用例、不重跑共享安装器矩阵或 collector 完整业务；N3/N4 仅在实际入口、payload 或配置受影响时定向复核，不因文档 SHA 变化重跑。

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

人工比对完整源目录与安装树；允许差异仅R3必要的七个同目录薄入口、固定运行环境与原文附录。检查 `scripts/stage5_immutable` 在安装树中存在、调用同目录 `stage5_immutable.py`，生成的 email-generator 角色从安装 skill 根目录以该入口调用 `stage5-finalize`，不再依赖 `skillrepo exec` 或开发 checkout；只核此静态调用关系，不增加 Stage 5 邮件业务执行。检查 `.agents/skills/professor-contact/scripts/_stage2_chatgpt_handoff_impl.py`、stage5_immutable.py、docs/stage5-legacy-contract.md存在，Stage5路由附录实际进入SKILL与coordinator正文；检查sentinel仍为keep。读依赖元数据确认collector/ contact-evidence、paper、Zotero、humanizer、vision、pdfx的llm-ocr-refresh、KB所选包真实递归安装；不同payload冲突不能记录成成功。

只核此环境具体生成的必要MCP表与上游正式输出相符，不重验共享installer保护全矩阵。模型/网络/审批保持既有设置。build/eval/apply分别记录，eval成功不能替代build。

N2 另外记录 handoff 薄入口的固定运行环境，供 N3 直接使用（只核这一条调用关系，不展开七个入口的运行矩阵）：

```sh
SKILL="$RUN/consumer/.agents/skills/professor-contact"
THIN="$SKILL/scripts/stage2_chatgpt_handoff"
grep -n 'CONTACT_PAPER_PYTHON' "$THIN" > "$RUN/output/n2-handoff-binding.txt"
FIXED_PYTHON="$(sed -n '1s/^#!//p' "$THIN")"
test -x "$FIXED_PYTHON"
printf '%s\n' "$FIXED_PYTHON" > "$RUN/output/n3-fixed-python.txt"
```

`n2-handoff-binding.txt` 必须显示该入口把 `CONTACT_PAPER_PYTHON` 绑定到运行时包的固定解释器，并与 `n3-fixed-python.txt` 为同一路径。原准备时点尚无实现，故保留以下绑定判据；当前实际绑定见执行记录 N2/N3：实现若用 shebang 以外的方式绑定，则记录实际绑定路径与它使用的解释器，并在结果中注明实际值，不猜默认值，也不预先断言该绑定形式必然失败。

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

PDF 样本自己生成，不依赖真实论文或上游检出：在临时运行目录里写一个小型单页合成 PDF，路径带空格以覆盖 argv 传递，然后用它的绝对路径写 papers.json（该项只看 router 是否选中已有 PDF，不解析 PDF 正文）：

```sh
PDF_DIR="$RUN/data/pdf sample"
mkdir -p "$PDF_DIR"
PDF_PATH="$(python3 - "$PDF_DIR/nix fixture paper.pdf" <<'PY'
from pathlib import Path
import sys
pdf = Path(sys.argv[1])
pdf.write_bytes(
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
print(pdf.resolve())
PY
)"
test -s "$PDF_PATH"
jq -n --arg pdf "$PDF_PATH" '[{item_key:"NIXTEST1", pdf_path:$pdf}]' > "$RUN/data/papers.json"
jq -e --arg pdf "$PDF_PATH" 'length == 1 and .[0].item_key == "NIXTEST1" and .[0].pdf_path == $pdf' \
  "$RUN/data/papers.json" > /dev/null
```

（`python3` 用系统解释器即可：这一步只写测试样本；`PDF_PATH` 取 `resolve()` 后的规范化绝对路径，与 router 输出里的 `paper` 字段同一写法。）

执行：

```sh
"$SKILL/scripts/stage2_input_router" --papers "$RUN/data/papers.json" --output-dir "$RUN/output/router" > "$RUN/output/routes.json"
jq -e --arg pdf "$PDF_PATH" '
  .status == "ok" and (.routes|length) == 1 and
  (.routes[0] | .item_key == "NIXTEST1" and .status == "ok" and .carrier == "pdf" and
    .level == "fulltext" and .paper == $pdf and .gap_only_allowed == true)
' "$RUN/output/routes.json" > /dev/null
test ! -e "$RUN/output/router/NIXTEST1.json"
```

确认NIXTEST1选中该PDF，不触发摘要导出（`$RUN/output/router` 下不出现该 key 的 JSON，也不调用 exporter）；文件路径/空格通过argv传递。该项检查安装入口，不检查PDF抽取准确性。

handoff 部分的安装态命令（在安装树内执行，读取的是安装后的 `$SKILL/scripts/stage2_chatgpt_handoff.py`，复用同一合法 facts/future-work 数据）：

```sh
FIXED_PYTHON="$(cat "$RUN/output/n3-fixed-python.txt")"
# 测试夹具自带的假 uv 会 exec python3；安装包不提供隐式 PATH，所以给本次测试加一个只含该解释器的 PATH 前缀
mkdir -p "$RUN/pathbin"
ln -sf "$FIXED_PYTHON" "$RUN/pathbin/python3"
export PATH="$RUN/pathbin:$PATH"
cd "$SKILL/tests"
{
  env -u CONTACT_PAPER_PYTHON "$FIXED_PYTHON" -B -m unittest -v \
    test_stage2_chatgpt_handoff.HandoffTests.test_future_work_selection_is_finalized_locally_via_uv_run
  CONTACT_PAPER_PYTHON="$FIXED_PYTHON" "$FIXED_PYTHON" -B -m unittest -v \
    test_stage2_chatgpt_handoff.HandoffTests.test_future_work_selection_is_finalized_locally_via_configured_python_backend
} 2>&1 | tee "$RUN/output/n3-handoff-unittest.log"
```

预期两条都实际执行并且 `ok`：第一条保留原 uv 默认后端断言（`uv run` 启动 `future_work.py` 与同目录 `facts.py`）；第二条绑定固定解释器后，`_run_future_work` 用 `[固定解释器, script, ...]` 启动两个 helper，fake uv 日志中没有这两次调用，facts 仍解析为同一 paper 安装的相邻脚本。第二条显示 `skipped` 记为未执行，不能写成通过。第二条断言只覆盖本次固定解释器适配，不把 fake helper 结果当真实导出验收；不扩大到全部 handoff suite。该断言的证明力如实限定为「绑定后不再经过 uv」——它不排除实现改用其它方式启动同一脚本；安装态真正绑定的固定解释器路径由 N2 的薄入口记录核对，两项合起来覆盖「helper 用固定环境」与「原 uv 默认路径保留」。

### N4：角色和真实导出

#### N4.1 安装角色一次真实 Codex 调用

准备现有第 53 号 Stage-4 fixture（安装树内的既有入口，合成数据，不读取真实教授资料）：

```sh
RUNTIME="$SKILL/tests/runtime"
VERIFY="$RUNTIME/verify_issue32_e2e.py"
PROGRAM="$RUN/data/selection-program"
PROFILE="$RUN/data/selection-profile"
PY="$(cat "$RUN/output/n3-fixed-python.txt")"
"$PY" -c 'import sys' || { echo "n3-fixed-python.txt 不是可用解释器：按 N2 记录的实际绑定值更正后重跑"; exit 1; }
"$PY" "$RUNTIME/prepare_issue53_stage4_fixture.py" \
  --program-root "$PROGRAM" --profile-root "$PROFILE" \
  --output "$RUN/output/selection-fixture.json"
"$PY" "$VERIFY" stage4-snapshot --program-root "$PROGRAM" \
  --output "$RUN/output/selection-pre-snapshot.json"
jq -e 'all(.artifacts[]; .exists == false)' "$RUN/output/selection-pre-snapshot.json"
```

样例必须放在消费者之外（`$RUN/data/`）：`tests/runtime/fixture_support.py::producer_root()` 取 `parents[5]`，在安装树里正是消费者根，样例放进消费者会被 `resolved_outside_producer` 直接拒绝。本用例预期零写入，沙盒只需可读，因此不必放进 `--cd` 工作区。

渲染固定提示词（第 53 号 prompt 的 `<PROGRAM_ROOT>` 占位符）：

```sh
"$PY" - "$RUNTIME/prompts/issue53-stage4-missing-selection.txt" \
  "$RUN/output/selection-prompt.txt" "$PROGRAM" <<'PY'
from pathlib import Path
import sys
src, out, root = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
text = src.read_text(encoding="utf-8")
if text.count("<PROGRAM_ROOT>") != 1:
    raise SystemExit("prompt must contain exactly one <PROGRAM_ROOT>")
out.write_text(text.replace("<PROGRAM_ROOT>", str(root)), encoding="utf-8")
PY
```

合并该 pin 的版本化夹具配置并记录生效配置（模型、推理、sandbox 与 V2 委派开关全部来自这一个文件）：

```sh
FIXTURES="${FIXTURES:?set skills-test-fixtures checkout absolute path}"
test "$(git -C "$FIXTURES" rev-parse HEAD)" = 8cecafc694e4591dee47372f38903e5ac2b689fe
mkdir -p "$RUN/consumer/.codex"
if [ -f "$RUN/consumer/.codex/config.toml" ]; then
  yq eval-all -p toml -o toml '. as $item ireduce ({}; . * $item)' \
    "$RUN/consumer/.codex/config.toml" "$FIXTURES/configs/codex-nested-delegation-consumer.toml" \
    > "$RUN/output/consumer-codex-config.toml"
else
  cp "$FIXTURES/configs/codex-nested-delegation-consumer.toml" \
    "$RUN/output/consumer-codex-config.toml"
fi
yq -p toml -e '
  .model == "gpt-6-luna" and .model_reasoning_effort == "low"
  and .sandbox_mode == "workspace-write" and .features.multi_agent_v2.enabled == true
' "$RUN/output/consumer-codex-config.toml"
cp "$RUN/output/consumer-codex-config.toml" "$RUN/consumer/.codex/config.toml"
```

构造唯一 `/eval` 请求：显式传入 `--sandbox workspace-write` 配合规范化的 `--cd` 路径、提示词与输出兼容参数；模型、推理及委派设置复用上一步项目配置，不追加 `--model`、`--ephemeral` 或 `--config`（含 trust）。第 53 号既有请求构造器 `build_issue53_eval_request.py` 固定 `gpt-5.6-luna` 与 dotted trust 写法，因此本项只复用它的 fixture、prompt 与判定器，请求按本轮已确认方式构造：

```sh
"$PY" - "$RUN/consumer" "$RUN/output/selection-prompt.txt" "$RUN/output/selection-request.json" <<'PY'
import json, shlex, sys
from pathlib import Path
consumer = Path(sys.argv[1]).resolve()
prompt = Path(sys.argv[2]).read_text(encoding="utf-8")
argv = [
    "--json", "--skip-git-repo-check",
    "--sandbox", "workspace-write", "--cd", str(consumer),
    "--", prompt,
]
Path(sys.argv[3]).write_text(
    json.dumps({"command": shlex.join(argv), "timeout": 900}, ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8",
)
PY
shasum -a 256 "$RUN/output/selection-fixture.json" "$RUN/output/selection-pre-snapshot.json" \
  "$RUN/output/selection-prompt.txt" "$RUN/output/selection-request.json" \
  "$RUN/output/consumer-codex-config.toml" > "$RUN/output/selection-input-sha256.txt"
```

该摘要文件只是本次准备的输入记录，不是通过条件，也不进入判定：判定以 `stage4-needs-input` 的输出为准。

执行唯一正式请求并判定（`case-started.txt` 紧接请求之前；此前失败均记未开始）：

```sh
HARNESS_WORKSPACE="${HARNESS_WORKSPACE:?set existing eval-server checkout absolute path}"
EVAL_PORT="$(direnv exec "$HARNESS_WORKSPACE" printenv EVAL_PORT)"
test -n "$EVAL_PORT"
touch "$RUN/output/selection-case-started.txt"
curl -sS --max-time 930 -o "$RUN/output/selection-eval-response.json" \
  -w '%{http_code}\n' -H 'Content-Type: application/json' \
  --data-binary @"$RUN/output/selection-request.json" \
  "http://127.0.0.1:$EVAL_PORT/eval" > "$RUN/output/selection-eval-http-status.txt"
"$PY" "$VERIFY" stage4-snapshot --program-root "$PROGRAM" \
  --output "$RUN/output/selection-post-snapshot.json"
"$PY" "$FIXTURES/scripts/parse_codex_eval_evidence.py" \
  --contract "$FIXTURES/configs/codex-eval-adapter-contract.json" \
  --eval-response "$RUN/output/selection-eval-response.json" \
  --consumer-root "$RUN/consumer" \
  --expected-agent professor-contact-selection \
  --output "$RUN/output/selection-adapter.json"
"$PY" "$VERIFY" stage4-needs-input --program-root "$PROGRAM" \
  --eval-response "$RUN/output/selection-eval-response.json" \
  --adapter-output "$RUN/output/selection-adapter.json" \
  --pre-snapshot "$RUN/output/selection-pre-snapshot.json" \
  --post-snapshot "$RUN/output/selection-post-snapshot.json" \
  --output "$RUN/output/selection-verdict.json"
jq -e '.status == "pass" and .classification == "PASS"' "$RUN/output/selection-verdict.json"
```

预期：root 原生委派安装的 `professor-contact-selection`，child 只返回一个业务 JSON，`result=needs_input` 且 `pending_selection` 与 fixture 当前候选状态逐字段一致（`kind="direction"`、`direction_ids=["DIR00001"]`，候选按 fixture 顺序为 `idea-001`、`idea-002`，由判定器从当前状态推导）；程序级 `教授研究/套磁选择.json`、`教授研究/邮件输入.json` 零写入（post 快照全 absent）。HTTP 非 2xx、适配器不可观察或快照不一致分别按阻塞/无效记录，不冒充产品失败：拿不到正式委派关系时判定器返回 blocked/BLOCKED_OBSERVABILITY，本项按未完成记录并写明缺的具体委派面，不改判为产品失败；项目配置或已安装角色实际未加载时，依据原始响应记录具体事实、阻塞/无法判断及证据位置，不推定原因、不新增预先信任证明或修改全局安全设置。检查一次实际结果即可，不循环调用 8 个角色、不测试整套委派拓扑。

#### N4.2 真实摘要导出（复用 PR90 recipe）

按 [PR90 recipe](../pr90-macos-real-abstract-export-recipe.md) 第 2 节（夹具 checkout、`prepare_shared_test_assets_macos.sh`、启动独立 Zotero 测试夹具）与第 3 节（写入一条有摘要无 PDF 的合成 item 并取 `ITEM_KEY`）原样执行，并传递该节导出的 `ZOTERO_HTTP_URL`/`ZOTERO_MCP_URL`；不执行第 1 节的 APM 重装，也不执行该 recipe 的其它测试。第 1 节里被第 2、3 节引用的变量改按本次 Nix 消费者取值：

```sh
CONSUMER="$RUN/consumer"
mkdir -p "$RUN/evidence"
ZOTERO_READ_SKILL="$CONSUMER/.agents/skills/zotero-read"
test -f "$ZOTERO_READ_SKILL/scripts/new-session.sh" \
  || { echo "缺少已安装 zotero-read 的 scripts/new-session.sh，本子项记未执行"; exit 1; }
```

安装的技能目录名与 N2 记录不一致时按实际路径设置 `ZOTERO_READ_SKILL`；缺该脚本时本子项记未执行并记录具体缺项，不自行发明会话创建方式。第 4 节改用本次安装的薄入口（Nix 入口自带锁定 exporter，因此不再传 `--zotero-read-skill-dir`，也不 mock）：

```sh
OUT="$RUN/output/abstract-export"
mkdir -p "$OUT/exports"
jq -n --arg key "$ITEM_KEY" '[{item_key:$key}]' > "$RUN/data/abstract-papers.json"
"$SKILL/scripts/stage2_input_router" \
  --papers "$RUN/data/abstract-papers.json" --output-dir "$OUT/exports" \
  > "$OUT/routes.json" 2> "$OUT/router.stderr"
jq -e --arg key "$ITEM_KEY" '
  .status == "ok" and (.routes|length) == 1 and
  (.routes[0] | .item_key == $key and .status == "ok" and
    .carrier == "abstract_json" and .level == "abstract")
' "$OUT/routes.json" > /dev/null
jq -e --arg key "$ITEM_KEY" --arg title "$EXPECTED_TITLE" --arg abstract "$EXPECTED_ABSTRACT" '
  .schema == 1 and .kind == "paper-analysis-input" and .source == "zotero" and
  .level == "abstract" and .item_key == $key and
  .metadata.title == $title and (.abstract|type) == "string" and
  (.abstract|length) > 0 and .abstract == $abstract
' "$OUT/exports/$key.json" > /dev/null
```

papers.json 只有该 key、不含 `pdf_path`/`ocr_path`。预期 router 行 `carrier=abstract_json`、`level=abstract`、`status=ok`，并写出与预置标题/摘要逐字节一致的规范化文件。服务不具备时该子项记未执行，不能拿 N3 的 PDF 路由充数，也不得用 mock 或空摘要代替。

## 4. 结果、重试和关闭

当前产品 `5032a28882a36789a8b0c81e8c25ed6233f8abd0` 已接入 collector，aarch64-darwin 完整 N1/N2 已有实际结果，N3/N4 沿用未受影响记录，见 [执行记录第 9 节](test-execution-2026-10-18.md#9-collector-接线与-n1n2-复核2026-10-18)。Gate1/Gate2 沿用正式审核通过结论，Gate3 待审核新结果及复用依据；本次仅同步事实，不自授结果通过。TP3 明确标出的两处 recipe 空缺已在本版补入：N3 的安装态执行命令与固定解释器断言、N4.1 的 selection fixture／请求／判定链；这是历史步骤修订说明；当前不重开已通过的 Gate1/Gate2，只审核上述实际结果与复用依据。

记录每项产品SHA、依赖pin、实际命令、结果、必要输出位置以及复用证据即可。引用共享agent-env TP1.1/Gate1/Gate2和上游已验结果，不自授PASS。未运行的OCR/真实论文分析/KB写入/下载/全套磁流程不能宣称通过。

本轮为 N3 增加了一条安装态断言（`.apm/skills/professor-contact/tests/test_stage2_chatgpt_handoff.py::HandoffTests.test_future_work_selection_is_finalized_locally_via_configured_python_backend`）：它以 `CONTACT_PAPER_PYTHON` 是否存在为前置——未绑定时该项不适用（普通检出与 CI 显示 skipped），只有安装薄入口绑定固定解释器后才执行，此处保留最初测试准备时的适用性设计；当前安装态执行结果见上述记录。因此 N3 记录必须显示该条实际执行（`... ok`）；只出现 `skipped` 时记未执行。

评估与夹具记录：保存 `/eval` 请求 JSON、事后响应、生效的 `consumer-codex-config.toml`、适配器输出与 `selection-verdict.json`；Zotero 子项保存 `routes.json`、导出文件与夹具 `fixture.env` 位置。敏感原始材料只留受控访问位置。预检记录在仓库外 `/tmp/pr93-te-precheck/`。

网络拉取或外部服务短暂故障恢复后允许同参数重试一次；业务断言失败先修复，不重复采样。Zotero只读导出，确认本次输出目录隔离后再重试，保留旧失败记录；不修改全局安全设置。没有新信息的持续外部故障停止受影响项。运行完成且无子线程使用后，只删除本次临时可变fixture，结果保留给审核；不终止用户进程、不清生产库。



