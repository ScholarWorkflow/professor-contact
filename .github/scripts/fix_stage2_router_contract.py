from pathlib import Path

path = Path('.apm/agents/professor-contact-analyzer.agent.md')
text = path.read_text(encoding='utf-8')
marker = '6. **本地 route → `paper-analysis full`（只处理 execution pass 剩余 jobs，批量并发 ≤3）**：\n'
if marker not in text:
    raise SystemExit('missing local route marker')
insert = r'''6. **本地 route → `paper-analysis full`（只处理 execution pass 剩余 jobs，批量并发 ≤3）**：
   - route 调用契约保持原样，继续一次批量调用：
     ```bash
     skillrepo exec professor-contact .apm/skills/professor-contact/scripts/stage2_input_router.py \
       --papers /tmp/<教授名>_<collection_key>_paper_routes.json \
       --output-dir /tmp/professor-contact-paper-inputs/<教授名>/<collection_key>
     ```
   - router stdout 仍只按三类消费：`carrier=ocr|pdf → level=fulltext, gap_only_allowed=true`；`carrier=abstract_json → level=abstract, gap_only_allowed=false`，且 `paper` 必须是 **normalized abstract JSON absolute path**；`status=error` 不 spawn 分析。
   - **绝不把 raw Zotero `item_key` 当作 `paper`**，也绝不把 abstract body 嵌进 task prompt；normalized exporter/router 失败就显式 partial/error，不恢复旧 raw-key fallback。
'''
text = text.replace(marker, insert, 1)
path.write_text(text, encoding='utf-8')
