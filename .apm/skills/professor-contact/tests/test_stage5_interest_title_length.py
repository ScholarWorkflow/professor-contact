"""Prepared test assets for requirement R1: a cited paper title does not count
toward the Stage-5 interest length.

These selectors belong to ``plan/interest-title-length/test-plan.md`` (T1-T4)
and are prepared, not executed. The shared validator still counts every
character of ``interest_sentences_ja``, so T1, T2 and T4 are expected to fail
as product-missing until it exempts a verbatim cited title. T3 guards the
preserved behaviour: it holds on the prepared baseline and on the intended
behaviour, and passing there is not evidence for R1.

The module reuses the existing Stage-5 fixture and wrapper helpers through
their module objects, so it adds no fixture, no installation and no model call.
"""
import copy
import json
import re
import unittest
from pathlib import Path

import test_contact_state as helpers
import test_stage5_immutable as immutable

BaseEnv = immutable.BaseEnv
parse = immutable.parse
run_wrapper = immutable.run_wrapper
contact_state = helpers.contact_state

#: The cited title the Stage-4 email pack carries for ``AAAA1111``.
TITLE = ("Synthetic comparison of input patterns across heterogeneous "
         "processing pipelines")

#: A title-shaped string that no email pack in this module ever carries.
FOREIGN_TITLE = ("An entirely unrelated synthetic study of pipeline behaviour "
                 "that the pack never mentions")

#: Neutral body text used only to reach an exact character count.
FILLER = "合成入力の比較を続けながら検討を進めております"

HEAD = "合成入力の比較に関心を持っております。"
CITED_HEAD = "先生のご論文「"
CITED_TAIL = "」を拝読し、比較の可能性に気づかされました。"
EXAMPLE = "例えば、別の合成入力でも同じ比較ができれば、といったことです。"

SURFACES = ("套磁邮件.md", "套磁邮件.txt", "套磁邮件状态.json")
FIXED_MARKERS = ("FIXED-BEGIN", "FIXED-SELFINTRO", "FIXED-INTEREST",
                 "FIXED-FUTURE", "FIXED-LEARNING", "FIXED-END")

#: The length requirement the rule must keep stating.
COUNT_WORDS = ("180", "字数", "文字数", "总长")
CLAUSE_SPLIT = re.compile(r"[；;。\n]")
#: A title word and an exemption word in one clause, in either order. The gap
#: allows a qualifier such as 「若与 papers[].title 逐字一致则」 but stops at a
#: clause boundary so a title in one sentence cannot borrow another's rule.
_TITLE = r"(?P<title>标题|タイトル|題名)"
_EXEMPT = (r"(?P<exempt>不计入|不计|免计|不算|不纳入|不计算|不参与|不占用|不列入"
           r"|排除|免除|除外|不含|以外|対象外|含めない|含まない|数えない"
           r"|除く|カウントしない|計上しない|計上いたしません)")
_GAP = r"[^、，,；;。\n]{0,30}?"
TITLE_EXEMPTION = re.compile(_TITLE + _GAP + _EXEMPT)
EXEMPTION_TITLE = re.compile(_EXEMPT + _GAP + _TITLE)
#: 「标题内方法名除外」 and 「标题内的限定语链不计」 exempt something *inside* a
#: title, so the window just before the exemption word decides the subject.
INSIDE_TITLE = re.compile(r"(标题|タイトル|題名)(内|中|里|の内)")
#: 「书名号内的论文标题不计」 and 「书名号以外的字符照常计数」 scope the symbols,
#: they do not exempt them, so the same guard applies to the symbol check. The
#: suffix may follow the symbol after a few characters, as in 「书名号以外的字符」.
SCOPED_SYMBOL = re.compile(
    r"(书名号|引号|标点|符号|括弧|括号|記号|句読点|「」)"
    r"[^、，,；;。\n]{0,6}?(内|中|里|以内|以外|之外|の内|の外)")
_SYMBOL = r"(?P<symbol>书名号|引号|标点|符号|括弧|括号|記号|句読点|「」)"
#: The gap excludes brackets on both sides so a title exemption cannot reach
#: across a parenthesis into the symbols mentioned outside it.
_SYMBOL_GAP = r"[^、，,；;。（()）\n]{0,10}?"
#: An exemption word near a bracket or punctuation word means those are
#: exempted too, which contradicts the requirement that they keep counting.
#: Both orders are checked because 「不计书名号与标点」 states the same thing.
SYMBOL_EXEMPTION = re.compile(_SYMBOL + _SYMBOL_GAP + _EXEMPT)
EXEMPTION_SYMBOL = re.compile(_EXEMPT + _SYMBOL_GAP + _SYMBOL)
#: 「书名号与标点（均不计）」 states the same exemption inside a parenthetical,
#: where the gap above deliberately refuses to reach.
SYMBOL_PAREN_EXEMPTION = re.compile(
    _SYMBOL + r"[^、，,；;。\n]{0,10}?[（(][^）)\n]{0,12}?" + _EXEMPT)
#: A parenthetical may also name the symbols again after the title
#: (「含标题与标点，均不计」), which puts them back inside the exemption.
_PAREN_SYMBOL = re.compile(r"书名号|引号|标点|符号|括弧|括号|記号|句読点|「」")


def _pad(text, length):
    """Grow ``text`` with neutral filler to exactly ``length`` characters."""
    if len(text) > length:
        raise AssertionError(f"{len(text)} characters already exceed {length}: {text}")
    need = length - len(text)
    return text + (FILLER * (need // len(FILLER) + 1))[:need]


def _clauses(rule):
    """Split a generated rule into clauses so wording must co-occur locally."""
    return [clause for clause in CLAUSE_SPLIT.split(rule) if clause.strip()]


def title_exemptions(rule):
    """Return the clauses that exempt a cited title from the count.

    This is an approximate reading of prose, not a semantic parser: it accepts
    a title word and an exemption word in one clause, in either order, and
    rejects a clause whose exemption is scoped inside a title
    (「标题内方法名除外」). The test only asks that the generated rule state the
    exemption at all; it does not certify the rule's wording.
    """
    found = []
    for clause in _clauses(rule):
        for pattern in (TITLE_EXEMPTION, EXEMPTION_TITLE):
            for match in pattern.finditer(clause):
                before = clause[max(0, match.start("exempt") - 10):match.start("exempt")]
                if INSIDE_TITLE.search(before):
                    continue
                found.append(clause)
    return found


def symbol_exemptions(rule):
    """Return the clauses that also exempt the brackets or punctuation.

    R1 keeps those characters counted, so a rule that exempts them contradicts
    the behaviour under test. The check is one-directional on purpose: it looks
    for an explicit exemption of a bracket or punctuation word and does not try
    to confirm positive "still counted" wording, which prose can express in too
    many ways to enumerate. A rule that never mentions the symbols at all
    therefore passes — that is a known, deliberate limit of this check, recorded
    in the test plan. A symbol word scoped by 内/中/里/以外 scopes the symbols
    rather than exempting them, so those matches are skipped.
    """
    found = []
    for clause in _clauses(rule):
        for pattern in (SYMBOL_EXEMPTION, EXEMPTION_SYMBOL, SYMBOL_PAREN_EXEMPTION):
            for match in pattern.finditer(clause):
                start = match.start("symbol")
                # Look at both sides of the symbol word: 「书名号以外」 puts the
                # scope marker after it, 「标题内书名号除外」 puts the guard before.
                window = clause[max(0, start - 12):start + 10]
                if SCOPED_SYMBOL.search(window):
                    continue
                # A parenthetical after the symbols may explain that the *title*
                # is exempt, which agrees with R1: 「标点照常计数（论文标题不计）」.
                # It does not agree when the parenthetical names the symbols again
                # after the title: 「含标题与标点，均不计」 exempts both.
                if pattern is SYMBOL_PAREN_EXEMPTION:
                    inside = clause[start:match.start("exempt")]
                    title_at = min((inside.find(word) for word in ("标题", "タイトル", "題名")
                                    if word in inside), default=-1)
                    if title_at >= 0 and not _PAREN_SYMBOL.search(inside[title_at:]):
                        continue
                found.append(clause)
    return found


def interest_corpus(title, net):
    """Return three interest sentences whose title-excluded length is ``net``.

    The title is quoted verbatim exactly once inside ②; every other character,
    including the brackets and the connectives around the citation, is ordinary
    body text and stays counted.
    """
    cited = CITED_HEAD + title + CITED_TAIL
    fixed = len(HEAD) + len(cited) - len(title) + len(EXAMPLE)
    extra = net - fixed
    if extra < 0:
        raise AssertionError(f"net {net} is below the fixed skeleton length {fixed}")
    first = extra // 2
    sentences = [_pad(HEAD, len(HEAD) + first), cited,
                 _pad(EXAMPLE, len(EXAMPLE) + extra - first)]
    total = sum(len(sentence) for sentence in sentences)
    if total - len(title) != net:
        raise AssertionError(f"corpus accounting: total {total} minus title "
                             f"{len(title)} is not {net}")
    if sum(sentence.count(title) for sentence in sentences) != 1:
        raise AssertionError("the title must be quoted verbatim exactly once")
    return sentences


class TestStage5InterestTitleLength(BaseEnv):
    """T1-T4: the net body length, not the title, decides the cap."""

    prepare = helpers.TestStage5.prepare
    raw_result = helpers.TestStage5.raw_result
    choices = helpers.TestStage5.choices

    def setUp(self):
        super().setUp()
        for paper in self.papers:
            if paper["item_key"] == "AAAA1111":
                paper["title"] = TITLE

    def pack_row(self):
        pack = json.loads(Path(self.email_pack).read_text(encoding="utf-8"))
        return pack["emails"][0]

    def pack_title(self, row):
        for paper in row.get("papers") or []:
            if paper.get("item_key") == "AAAA1111":
                return paper["title"]
        raise AssertionError(f"the pack carries no title for AAAA1111: {row.get('papers')}")

    def write_inputs(self, raw, choices=None):
        raw_path = self.root / "raw.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        choice_path = self.root / "choices.json"
        choice_path.write_text(
            json.dumps(choices or self.choices(), ensure_ascii=False), encoding="utf-8")
        return raw_path, choice_path

    def problems(self, row, raw):
        """Every validator problem for a raw result that is otherwise valid.

        The fixture supplies a legal three-part result, a legal ``source_map``
        and matching ids, so a non-empty list here is a length verdict and not
        a second, unrelated contract check. Reading the whole list also keeps
        the assertion independent of the implementer's message wording.
        """
        return contact_state.validate_email_raw(row, raw)

    def assert_reported_net(self, problems, net):
        """The length verdict reports the title-excluded body length.

        The sentence itself is the implementer's choice, so the check reads the
        numbers it carries instead of matching its wording. Requiring the net
        number keeps the baseline visible: there the message still reports the
        total including the title (``interest total 260 ...``), so a net length
        of 181 never appears. Extra numbers, such as the cap itself, are fine.
        """
        self.assertEqual(len(problems), 1, problems)
        numbers = {int(value) for value in re.findall(r"\d+", problems[0])}
        self.assertIn(net, numbers, problems[0])

    def test_t1_long_cited_title_is_accepted_and_rendered_verbatim(self):
        g1 = self.prepare()
        row = self.pack_row()
        title = self.pack_title(row)
        self.assertEqual(title, TITLE)
        sentences = interest_corpus(title, 180)
        total = sum(len(sentence) for sentence in sentences)
        self.assertGreater(total, 200)
        self.assertLessEqual(total - len(title), 180)

        # The shared validator is the same code plan and finalize call, so the
        # accept decision is read there and the write path below only proves the
        # accepted body reaches the files unchanged.
        raw = self.raw_result(g1)
        raw["interest_sentences_ja"] = sentences
        self.assertEqual(self.problems(row, raw), [])

        raw_path, choice_path = self.write_inputs(raw)
        out = parse(run_wrapper("stage5-finalize", "--program-root", self.root,
                                "--email-pack", self.email_pack,
                                "--result", raw_path, "--choices", choice_path))
        self.assertEqual(out["status"], "ok", out)
        txt = (self.prof_dir / "套磁邮件.txt").read_text(encoding="utf-8")
        self.assertIn("\n".join(sentences), txt)
        self.assertIn(title, txt)
        for marker in FIXED_MARKERS:
            self.assertIn(marker, txt)
        self.assertIn(title, (self.prof_dir / "套磁邮件.md").read_text(encoding="utf-8"))

    def test_t1_generated_rule_states_the_title_exemption(self):
        self.prepare()
        plan = parse(run_wrapper("stage5-plan", "--program-root", self.root,
                                 "--email-pack", self.email_pack))
        rule = plan["jobs"][0]["model_input"]["rules"]["interest"]
        # The length requirement stays stated, the cited title is exempted, and
        # the brackets and punctuation around it are not exempted with it.
        self.assertTrue(any(word in rule for word in COUNT_WORDS), rule)
        self.assertTrue(title_exemptions(rule), rule)
        self.assertEqual(symbol_exemptions(rule), [], rule)

    def test_t2_net_body_thresholds_are_180_181_200_201(self):
        g1 = self.prepare()
        row = self.pack_row()
        title = self.pack_title(row)
        self.assertEqual(contact_state.INTEREST_SOFT_CAP, 180)
        self.assertEqual(contact_state.INTEREST_HARD_CAP, 200)
        for net, soft in ((180, False), (181, True), (200, True), (201, False)):
            with self.subTest(net=net):
                raw = self.raw_result(g1)
                raw["interest_sentences_ja"] = interest_corpus(title, net)
                total = sum(len(sentence) for sentence in raw["interest_sentences_ja"])
                self.assertGreater(total, net)
                problems = self.problems(row, raw)
                if net == 180:
                    self.assertEqual(problems, [])
                    continue
                self.assert_reported_net(problems, net)
                self.assertEqual(problems[0].startswith("WARNING"), soft, problems[0])

    def test_t3_foreign_quoted_title_is_not_exempt(self):
        g1 = self.prepare()
        row = self.pack_row()
        self.assertNotIn(FOREIGN_TITLE, [paper.get("title") for paper in row.get("papers") or []])
        raw = self.raw_result(g1)
        raw["interest_sentences_ja"] = interest_corpus(FOREIGN_TITLE, 201)
        total = sum(len(sentence) for sentence in raw["interest_sentences_ja"])
        self.assertGreater(total, 200)
        problems = self.problems(row, raw)
        self.assert_reported_net(problems, total)
        self.assertFalse(problems[0].startswith("WARNING"), problems[0])

    def test_t3_pack_without_titles_keeps_the_original_counting(self):
        g1 = self.prepare()
        row = copy.deepcopy(self.pack_row())
        row["papers"] = []
        raw = self.raw_result(g1)
        raw["interest_sentences_ja"] = interest_corpus(TITLE, 180)
        total = sum(len(sentence) for sentence in raw["interest_sentences_ja"])
        self.assertGreater(total, 200)
        problems = self.problems(row, raw)
        self.assert_reported_net(problems, total)
        self.assertFalse(problems[0].startswith("WARNING"), problems[0])

    def test_t4_over_cap_finalize_is_rejected_without_rewriting_existing_email(self):
        g1 = self.prepare()
        row = self.pack_row()
        title = self.pack_title(row)
        raw = self.raw_result(g1)
        # The committed baseline cites the same title with a short body, so the
        # only difference between the accepted and the rejected run is length.
        baseline = interest_corpus(title, 100)
        self.assertLessEqual(sum(len(sentence) for sentence in baseline), 180)
        raw["interest_sentences_ja"] = baseline
        raw_path, choice_path = self.write_inputs(raw)
        args = ("stage5-finalize", "--program-root", self.root,
                "--email-pack", self.email_pack,
                "--result", raw_path, "--choices", choice_path)
        self.assertEqual(parse(run_wrapper(*args))["status"], "ok")
        surfaces = [self.prof_dir / name for name in SURFACES]
        before = {path: path.read_bytes() for path in surfaces}
        self.assertTrue(all(before.values()))

        raw["interest_sentences_ja"] = interest_corpus(title, 201)
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        rejected = run_wrapper(*args)
        self.assertNotEqual(rejected.returncode, 0)
        payload = json.loads(rejected.stdout)
        self.assertEqual(payload["status"], "error", payload)
        self.assertEqual(payload["reason_code"], "invalid_result_json", payload)
        # The message must carry the net length: the baseline reports only the
        # total of 281, which is what makes this a product-missing failure.
        self.assertIn("201", payload["message"])
        self.assertEqual(before, {path: path.read_bytes() for path in surfaces})


if __name__ == "__main__":
    unittest.main()
