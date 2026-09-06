"""Shared fixtures for the Stage-2 ChatGPT handoff regression tests.

The filename deliberately does not match the unittest discovery pattern
(``test_*.py``), so this module is never collected as a test.
"""

import os
import stat
from pathlib import Path

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

FAKE_UV_SCRIPT = (
    "#!/bin/sh\n"
    "printf '%s\\n' \"$*\" >> \"$UV_TEST_LOG\"\n"
    "[ \"$1\" = \"run\" ] || exit 2\n"
    "shift\n"
    "exec python3 \"$@\"\n"
)


class Args:
    """Plain attribute holder matching the handoff CLI argument contract."""


def write_fake_facts_script(root):
    """Write the fake facts helper into ``root`` and return its path.

    The fake facts.py must stay a sibling of the fake future-work helper: the
    importer derives it from the future-work script directory so both helpers
    always come from one paper-analysis install. The real helper is a 0644
    PEP-723 script that must be invoked as ``uv run <script> ...``, so the
    fake stays non-executable.
    """
    path = Path(root) / "facts.py"
    path.write_text(FAKE_FACTS_SCRIPT, encoding="utf-8")
    path.chmod(0o644)
    return path


class FakeUvEnvironment:
    """Tiny fake ``uv`` on PATH: logs its arguments to ``UV_TEST_LOG`` and
    execs the requested script with ``python3``.

    ``install()`` must be paired with ``restore()`` (setUp/tearDown) so PATH
    and UV_TEST_LOG never leak between tests.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.uv_log = self.root / "uv.log"
        self._old_path = None
        self._old_uv_test_log = None

    def install(self):
        self._old_path = os.environ.get("PATH", "")
        self._old_uv_test_log = os.environ.get("UV_TEST_LOG")
        fake_bin = self.root / "bin"
        fake_bin.mkdir(exist_ok=True)
        fake_uv = fake_bin / "uv"
        fake_uv.write_text(FAKE_UV_SCRIPT, encoding="utf-8")
        fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)
        os.environ["PATH"] = str(fake_bin) + os.pathsep + self._old_path
        os.environ["UV_TEST_LOG"] = str(self.uv_log)

    def restore(self):
        os.environ["PATH"] = self._old_path
        if self._old_uv_test_log is None:
            os.environ.pop("UV_TEST_LOG", None)
        else:
            os.environ["UV_TEST_LOG"] = self._old_uv_test_log
