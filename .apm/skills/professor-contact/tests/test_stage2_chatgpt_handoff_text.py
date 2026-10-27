"""Direct text transport, in-place source and legacy compatibility checks."""
import json
import subprocess
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import test_stage2_chatgpt_handoff as existing
import _stage2_handoff_test_support as support

handoff = existing.handoff


class TextTransportTests(unittest.TestCase):
    def setUp(self):
        self.f = existing.HandoffTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.prepared = json.loads(self.f.prepared.read_text())
        self.prepared.update(page_count=2,
            source_pages=[{'page': 1, 'text': 'Original paper sentence.'}, {'page': 2, 'text': ''}],
            page_quality=[{'page': 1, 'tier': 'trusted'}, {'page': 2, 'tier': 'empty'}])
        self.save()

    def save(self):
        self.f.prepared.write_text(json.dumps(self.prepared))

    def build(self, extra=()):
        args = support.Args()
        args.professor_dir = self.f.prof
        args.jobs = self.f.root / 'new-jobs.json'
        args.jobs.write_text(json.dumps({'schema': 1, 'jobs': [self.f._pdf_job(), *extra]}))
        args.professor = None
        support.add_paper_context(args, self.f.root)
        return handoff.build_bundle(args)

    def test_text_only_and_original_source_record_with_allowed_blank_page(self):
        original = self.f.pdf.read_bytes()
        result = self.build([{'item_key': 'ZZABS', 'carrier': 'abstract_json', 'level': 'abstract',
                              'input_path': str(self.f.abstract), 'analysis_relpath': '论文分析/A/Abs.md'}])
        self.assertTrue(result['upload_ready'])
        record = json.loads(Path(result['local_manifest_path']).read_text())
        job = record['manifest']['jobs'][0]
        self.assertEqual(record['sources']['ABC'], str(self.f.pdf))
        self.assertEqual(job['input_sha256'], handoff._sha256_file(self.f.pdf))
        self.assertTrue(job['expected']['facts'])
        self.assertTrue(job['expected']['future_work'])
        self.assertEqual(job['text_transport']['missing_text_pages'], [2])
        with zipfile.ZipFile(result['bundle_path']) as zf:
            self.assertIn('papers/ZZABS/paper-analysis-input.json', zf.namelist())
            self.assertFalse(any(n.endswith(('.pdf', '.png', '.jpg', '.local.json')) for n in zf.namelist()))
            text = zf.read(job['text_transport']['path']).decode()
            self.assertIn('Original paper sentence.', text)
            self.assertIn('<!-- PDF_PAGE: 2 -->', text)
            self.assertNotIn(str(self.f.pdf), ''.join(zf.read(n).decode() for n in zf.namelist()))
        self.assertFalse(list((self.f.prof / '论文分析/_chatgpt_handoff').rglob('*.pdf')))
        self.assertEqual(self.f.pdf.read_bytes(), original)

    def test_old_prepare_regenerates_full_prepare_from_installed_helper(self):
        self.prepared.pop('source_pages'); self.save()
        def run(script, *args):
            self.assertEqual(script.name, 'future_work.py')
            self.assertEqual(args[0], 'prepare')
            debug = Path(args[args.index('--debug-dir') + 1])
            debug.mkdir(parents=True, exist_ok=True)
            payload = {**self.prepared,
                       'source_pages': [{'page': 1, 'text': 'Original paper sentence.'},
                                        {'page': 2, 'text': ''}]}
            (debug / 'prepare.json').write_text(json.dumps(payload))
            (debug / 'candidates.json').write_text(json.dumps({'candidates': payload['candidates']}))
            return subprocess.CompletedProcess([], 0)
        with patch.object(handoff._impl, '_run_future_work', side_effect=run) as mock:
            self.assertTrue(self.build()['upload_ready'])
        self.assertEqual(mock.call_count, 1)

    def test_fulltext_cache_only_fills_bad_pages_through_merge(self):
        Path(str(self.f.pdf) + '.llm_ocr.txt').write_text('cache')
        for valid in (True, False):
            with self.subTest(valid=valid):
                def run(script, *args):
                    if args[0] == 'validate-fulltext-ocr-cache':
                        if valid:
                            Path(args[args.index('--output') + 1]).write_text(
                                '<!-- PDF_PAGE: 1 -->\nCached exact page\n<!-- PDF_PAGE: 2 -->\nCached second page')
                        return subprocess.CompletedProcess([], 0 if valid else 1)
                    self.assertEqual(args[0], 'merge-ocr')
                    prepared = json.loads(Path(args[args.index('--prepared') + 1]).read_text())
                    ocr = json.loads(Path(args[args.index('--ocr') + 1]).read_text())
                    for page in prepared['source_pages']:
                        text = ocr['pages'].get(str(page['page']))
                        if text is not None:
                            page['text'] = text
                    prepared['ocr_required_pages'] = []
                    prepared['ocr_resolved_pages'] = sorted(
                        set(prepared.get('ocr_resolved_pages') or [])
                        | {int(page) for page in ocr['pages']})
                    return subprocess.CompletedProcess([], 0, json.dumps(prepared))
                with patch.object(handoff._impl, '_run_future_work', side_effect=run):
                    result = self.build()
                self.assertTrue(result['upload_ready'])
                with zipfile.ZipFile(result['bundle_path']) as zf:
                    text = zf.read('papers/ABC/paper.txt').decode()
                pages = handoff._impl._text.page_texts(text, 2)
                # A cached full text never overwrites readable prepared pages; it
                # only supplies exact text for a bad page, then merge-ocr updates
                # the prepare the transport and the evidence share.
                self.assertEqual(pages[1].strip(), 'Original paper sentence.')
                self.assertEqual(pages[2].strip(), 'Cached second page' if valid else '')
                self.assertEqual(
                    self.f._manifest(result)['jobs'][0]['text_transport']['missing_text_pages'],
                    [] if valid else [2],
                )

    def test_page_cache_resolves_bad_page_through_merge(self):
        self.prepared['page_quality'][0]['tier'] = 'untrusted'
        self.prepared['ocr_resolved_pages'] = [1]
        self.prepared.pop('source_pages'); self.save()
        def run(script, *args):
            if args[0] == 'prepare':
                debug = Path(args[args.index('--debug-dir') + 1])
                debug.mkdir(parents=True, exist_ok=True)
                payload = {**self.prepared,
                           'source_pages': [{'page': 1, 'text': 'broken'},
                                            {'page': 2, 'text': ''}]}
                (debug / 'prepare.json').write_text(json.dumps(payload))
                (debug / 'candidates.json').write_text(json.dumps({'candidates': payload['candidates']}))
                return subprocess.CompletedProcess([], 0)
            if args[0] == 'validate-ocr-cache':
                Path(args[args.index('--output') + 1]).write_text(
                    json.dumps({'pages': {'2': 'Exact second OCR page'}}))
                return subprocess.CompletedProcess([], 0)
            self.assertEqual(args[0], 'merge-ocr')
            prepared = json.loads(Path(args[args.index('--prepared') + 1]).read_text())
            ocr = json.loads(Path(args[args.index('--ocr') + 1]).read_text())
            for page in prepared['source_pages']:
                text = ocr['pages'].get(str(page['page']))
                if text is not None:
                    page['text'] = text
            prepared['ocr_required_pages'] = []
            prepared['ocr_resolved_pages'] = sorted(
                set(prepared.get('ocr_resolved_pages') or [])
                | {int(page) for page in ocr['pages']})
            return subprocess.CompletedProcess([], 0, json.dumps(prepared))
        with patch.object(handoff._impl, '_run_future_work', side_effect=run):
            self.assertFalse(self.build()['upload_ready'])  # no page cache yet
            Path(str(self.f.pdf) + '.llm_ocr.pages.json').write_text(json.dumps({
                'schema': 1, 'pdf_sha256': handoff._sha256_file(self.f.pdf),
                'pages': {'2': 'Exact second OCR page'}}))
            result = self.build()
            self.assertTrue(result['upload_ready'])
        with zipfile.ZipFile(result['bundle_path']) as zf:
            self.assertIn(b'Exact second OCR page', zf.read('papers/ABC/paper.txt'))

    def test_required_pages_leave_continue_lease_without_upload(self):
        self.prepared['ocr_required_pages'] = [2]; self.save()
        result = self.build()
        self.assertFalse(result['upload_ready'])
        self.assertIsNone(result['bundle_path'])
        self.assertEqual(result['text_preparation'][0]['pages'], [2])
        lease = handoff.acquire_local_lease(self.f.prof, 'text-test', verify_plan=True,
            expected_handoff_id=result['handoff_id'], expected_source_fingerprint=result['source_fingerprint'])
        self.assertEqual(lease['status'], 'acquired')
        handoff.release_local_lease(self.f.prof, 'text-test')

    def test_new_import_finalizes_against_original(self):
        result = self.build()
        job = self.f._manifest(result)['jobs'][0]
        returned = self.f._result_zip(result, [{'job_id': job['job_id'], 'item_key': job['item_key'],
                                               'input_sha256': job['input_sha256'], 'status': 'ok'}])
        self.assertEqual(self.f._import(result, returned)['status'], 'imported')
        facts = json.loads((self.f.prof / '论文分析/A/T.md.facts.json').read_text())
        self.assertEqual(facts['input_fingerprint'], 'sha256:' + job['input_sha256'])
        self.assertIn(str(self.f.pdf), self.f.uv_log.read_text())

    def test_changed_or_missing_source_rejected_without_install(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                self.f.pdf.write_bytes(b'%PDF-1.4\nbody')
                result = self.build(); job = self.f._manifest(result)['jobs'][0]
                returned = self.f._result_zip(result, [{'job_id': job['job_id'], 'item_key': 'ABC', 'input_sha256': job['input_sha256'], 'status': 'ok'}])
                if missing:
                    self.f.pdf.unlink()
                else:
                    self.f.pdf.write_bytes(b'%PDF changed')
                output = self.f._import(result, returned)
                self.assertEqual(output['reason_code'], 'external_result_hash_mismatch')
                self.assertFalse((self.f.prof / '论文分析/A/T.md').exists())

    def test_changed_text_rejected_without_install(self):
        result = self.build(); job = self.f._manifest(result)['jobs'][0]
        returned = self.f._result_zip(result, [{'job_id': job['job_id'], 'item_key': 'ABC', 'input_sha256': job['input_sha256'], 'status': 'ok'}])
        path = Path(result['bundle_path'])
        with zipfile.ZipFile(path) as zf:
            files = {n: zf.read(n) for n in zf.namelist()}
        files[job['text_transport']['path']] = b'changed'
        with zipfile.ZipFile(path, 'w') as zf:
            for n, data in files.items(): zf.writestr(n, data)
        self.assertEqual(self.f._import(result, returned)['reason_code'], 'external_result_hash_mismatch')
        self.assertFalse((self.f.prof / '论文分析/A/T.md').exists())


if __name__ == '__main__':
    unittest.main()
