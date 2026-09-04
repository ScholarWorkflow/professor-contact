import importlib.util
import json
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage2_chatgpt_handoff.py"
SPEC = importlib.util.spec_from_file_location("stage2_chatgpt_handoff_review4", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(handoff)

ANALYSIS = """# Paper

## 总结
summary
## 问题是什么
q
## 挑战是什么
c
## Solution 是什么
s
## 研究方法是什么
m
## 贡献是什么
x
## 局限性与批判性评价
l
## 作者明说的未来工作（Future Work）
—（论文未明示 future work）
## 对自身研究的帮助评估
h
"""

FACTS_DRAFT = {
    "paper": {"title": "Paper", "authors": ["Author A"], "year": 2024, "venue": "Venue", "doi": None},
    "research_problem": "problem",
    "research_object": "object",
    "approach": "approach",
    "findings": ["finding"],
    "contributions": ["contribution"],
    "topic_terms": ["topic"],
    "limitations": ["limitation"],
    "confidence": 0.8,
}

FAKE_FACTS_SCRIPT = (
    "#!/usr/bin/env python3\n"
    "import hashlib,json,pathlib,sys\n"
    "cmd=sys.argv[1]\n"
    "def arg(n): return pathlib.Path(sys.argv[sys.argv.index(n)+1])\n"
    "if cmd=='validate':\n"
    " d=json.loads(arg('--draft').read_text()); print(json.dumps({'ok':True,'facts':d}))\n"
    "elif cmd=='finalize':\n"
    " a=arg('--analysis'); draft=json.loads(arg('--draft').read_text());\n"
    " side=json.loads(arg('--future-work').read_text());\n"
    " assert side.get('status')=='ok' and side.get('analysis')==a.name, 'sidecar mismatch';\n"
    " fp='sha256:'+hashlib.sha256(arg('--input').read_bytes()).hexdigest();\n"
    " ids=[i.get('id') for i in side.get('items',[]) if i.get('id')];\n"
    " out={'schema':1,'kind':'paper-analysis-facts','generator_version':'facts-v1','analysis':a.name,'input_fingerprint':fp,'evidence_level':'fulltext','status':'ok'};\n"
    " out.update(draft); out['future_work_ids']=ids;\n"
    " pathlib.Path(str(a)+'.facts.json').write_text(json.dumps(out),encoding='utf-8');\n"
    " print(json.dumps({'ok':True}))\n"
)


class Args:
    pass


class Review4RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prof = self.root / "Professor"
        (self.prof / "论文分析").mkdir(parents=True)
        self.pdf = self.root / "paper.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nbody")
        self.prepare = self.root / "prepare.json"
        self.candidates = self.root / "candidates.json"

        self.future = self.root / "future-work"
        self.future.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib,json,pathlib,re,sys,unicodedata\n"
            "cmd=sys.argv[1]\n"
            "def arg(n): return pathlib.Path(sys.argv[sys.argv.index(n)+1])\n"
            "def norm(s): return re.sub(r'\\s+',' ',unicodedata.normalize('NFKC',s).strip())\n"
            "if cmd=='merge-ocr':\n"
            " p=json.loads(arg('--prepared').read_text()); o=json.loads(arg('--ocr').read_text());\n"
            " req=set(p.get('ocr_required_pages',[])); keep=[x for x in p.get('candidates',[]) if x.get('page') not in req]; made=[]\n"
            " for raw_page,text in o['pages'].items():\n"
            "  page=int(raw_page); q=norm(text); made.append({'id':hashlib.sha256(q.encode()).hexdigest(),'quote':q,'page':page})\n"
            " p['candidates']=keep+made; p['ocr_required_pages']=[]; p['ocr_resolved_pages']=sorted(int(x) for x in o['pages']); print(json.dumps(p))\n"
            "elif cmd=='validate':\n"
            " items=json.loads(arg('--items').read_text()).get('items',[]); c=json.loads(arg('--candidates').read_text()).get('candidates',[]);\n"
            " loc={(norm(x['quote']),x['page']) for x in c}; assert all((norm(x['quote']),x['page']) in loc for x in items); print(json.dumps({'result':'ok'}))\n"
            "elif cmd=='finalize':\n"
            " a=arg('--analysis'); items=json.loads(arg('--items').read_text()).get('items',[]); side=pathlib.Path(str(a)+'.future_work.json');\n"
            " side.write_text(json.dumps({'schema':1,'status':'ok','analysis':a.name,'items':items}),encoding='utf-8'); print(json.dumps({'result':'ok'}))\n",
            encoding="utf-8",
        )
        self.future.chmod(0o644)
        self.facts_script = self.root / "facts.py"
        self.facts_script.write_text(FAKE_FACTS_SCRIPT, encoding="utf-8")
        self.facts_script.chmod(0o644)

        self.old_path = os.environ.get("PATH", "")
        self.old_uv_test_log = os.environ.get("UV_TEST_LOG")
        self.uv_log = self.root / "uv.log"
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake_uv = fake_bin / "uv"
        fake_uv.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$UV_TEST_LOG\"\n"
            "[ \"$1\" = \"run\" ] || exit 2\n"
            "shift\n"
            "exec python3 \"$@\"\n",
            encoding="utf-8",
        )
        fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)
        os.environ["PATH"] = str(fake_bin) + os.pathsep + self.old_path
        os.environ["UV_TEST_LOG"] = str(self.uv_log)

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        if self.old_uv_test_log is None:
            os.environ.pop("UV_TEST_LOG", None)
        else:
            os.environ["UV_TEST_LOG"] = self.old_uv_test_log
        self.temp.cleanup()

    def _write_pair(self, prepare_candidates, standalone_candidates, required_pages=(2,)):
        self.prepare.write_text(json.dumps({
            "schema": 1,
            "pdf_sha256": handoff._sha256_file(self.pdf),
            "selection": {"pages": [1, 2]},
            "ocr_required_pages": list(required_pages),
            "candidates": prepare_candidates,
        }), encoding="utf-8")
        self.candidates.write_text(
            json.dumps({"candidates": standalone_candidates}), encoding="utf-8"
        )

    def _build(self, *, key="MIX"):
        jobs = self.root / "jobs.json"
        jobs.write_text(json.dumps({
            "schema": 1,
            "professor": "Professor",
            "jobs": [{
                "item_key": key,
                "carrier": "pdf",
                "level": "fulltext",
                "input_path": str(self.pdf.resolve()),
                "analysis_relpath": f"论文分析/A/{key}.md",
                "research_direction": {},
                "future_work_prepare": str(self.prepare.resolve()),
                "future_work_candidates": str(self.candidates.resolve()),
            }],
        }), encoding="utf-8")
        args = Args()
        args.professor_dir = self.prof
        args.jobs = jobs
        args.professor = None
        return handoff.build_bundle(args)

    def _manifest(self, bundle):
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            return json.loads(zf.read("manifest.json"))

    def _result(self, bundle):
        manifest = self._manifest(bundle)
        job = manifest["jobs"][0]
        safe = handoff._safe_component(job["job_id"])
        result = self.root / "result.zip"
        with zipfile.ZipFile(result, "w") as zf:
            zf.writestr("result_manifest.json", json.dumps({
                "schema": 1,
                "kind": handoff.RESULT_KIND,
                "handoff_id": manifest["handoff_id"],
                "source_fingerprint": manifest["source_fingerprint"],
                "results": [{
                    "job_id": job["job_id"],
                    "item_key": job["item_key"],
                    "input_sha256": job["input_sha256"],
                    "status": "ok",
                }],
            }))
            zf.writestr(f"results/{safe}/analysis.md", ANALYSIS)
            zf.writestr(
                f"results/{safe}/future_work_ocr.json",
                json.dumps({"pages": {"2": "We plan to extend the system to multilingual settings."}}),
            )
            zf.writestr(
                f"results/{safe}/future_work_selections.json",
                json.dumps({"items": [{
                    "page": 2,
                    "quote_excerpt": "extend the system to multilingual",
                    "translation_zh": "我们计划把系统扩展到多语言场景。",
                    "source": "Conclusion",
                }]}),
            )
            zf.writestr(
                f"results/{safe}/future_work_items.json",
                json.dumps({"items": [{
                    "page": 1,
                    "quote": "We will evaluate the framework on larger datasets.",
                    "translation_zh": "我们将用更大规模的数据集评估该框架。",
                    "source": "Conclusion",
                }]}),
            )
            zf.writestr(f"results/{safe}/facts.json", json.dumps(FACTS_DRAFT))
        return result

    def _import(self, bundle, result):
        args = Args()
        args.professor_dir = self.prof
        args.bundle = Path(bundle["bundle_path"])
        args.result = result
        args.future_work_script = self.future
        return handoff.import_result(args)

    def test_mixed_readable_and_ocr_pages_preserve_both_future_work_items(self):
        readable = {
            "id": "readable",
            "quote": "We will evaluate the framework on larger datasets.",
            "page": 1,
        }
        garbled = {"id": "garbled", "quote": "garbled extraction", "page": 2}
        self._write_pair([readable, garbled], [readable, garbled])
        bundle = self._build()
        job = self._manifest(bundle)["jobs"][0]
        self.assertEqual(job["future_work"]["selection_contract"], "ocr-excerpt-v1")
        with zipfile.ZipFile(bundle["bundle_path"]) as zf:
            instructions = zf.read("instructions.md").decode("utf-8")
        self.assertIn("readable page", instructions)
        self.assertIn("future_work_items.json", instructions)

        out = self._import(bundle, self._result(bundle))
        self.assertEqual(out["status"], "imported")
        sidecar = Path(str(self.prof / "论文分析/A/MIX.md") + ".future_work.json")
        items = json.loads(sidecar.read_text(encoding="utf-8"))["items"]
        self.assertEqual({item["page"] for item in items}, {1, 2})
        self.assertIn("larger datasets", next(item["quote"] for item in items if item["page"] == 1))
        self.assertIn("multilingual settings", next(item["quote"] for item in items if item["page"] == 2))
        calls = self.uv_log.read_text(encoding="utf-8")
        self.assertIn("merge-ocr", calls)
        self.assertIn("validate", calls)
        self.assertIn("finalize", calls)

    def test_build_rejects_cross_wired_prepare_and_candidates_pair(self):
        prepare_candidate = {
            "id": "paper-a",
            "quote": "We will evaluate the framework on larger datasets.",
            "page": 1,
        }
        other_candidate = {
            "id": "paper-b",
            "quote": "We will deploy the system in production.",
            "page": 1,
        }
        self._write_pair([prepare_candidate], [other_candidate], required_pages=())
        with self.assertRaisesRegex(ValueError, "candidate sets differ"):
            self._build(key="CROSS")
        self.assertFalse((self.prof / "论文分析/_chatgpt_handoff").exists())


if __name__ == "__main__":
    unittest.main()
