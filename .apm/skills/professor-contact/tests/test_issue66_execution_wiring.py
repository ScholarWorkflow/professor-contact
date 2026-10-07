"""确定性接线检查；不连接评测服务。"""
import importlib.util
import base64
import json
import shlex
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

PATH = Path(__file__).parent / 'runtime/issue66_execution.py'
spec = importlib.util.spec_from_file_location('issue66_execution', PATH)
wiring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wiring)


class ExecutionWiringTests(unittest.TestCase):
    def fresh_execution(self, directory, product_source="refs/pr73-current",
                        mode="installation-check", consumer=None):
        from argparse import Namespace
        root = Path(directory)
        execution = wiring.Execution(Namespace(repository=str(PATH.parents[5]),
            fixture_root=str(root), evidence_dir=str(root / 'evidence'),
            mode=mode, consumer=consumer,
            product_source=product_source))
        execution.provenance = {
            'test_source': {'root': str(PATH.parents[5])},
            'fixture_source': {'root': str(root)},
        }
        return execution

    def execution(self, directory, product_source="refs/pr73-current"):
        execution = self.fresh_execution(directory, product_source)
        execution.consumer.mkdir()
        return execution

    def formal_execution(self, directory):
        execution = self.execution(directory)
        wiring.write(execution.out / 'request.json', {'command': 'mock-only'})
        return execution

    def assert_transport_terminal(self, execution, expected):
        verdict = json.loads((execution.out / 'verdict.json').read_text())
        attempt = json.loads((execution.out / 'attempt.json').read_text())
        transport = json.loads((execution.out / 'transport.json').read_text())
        self.assertEqual(verdict['classification'], expected)
        self.assertNotIn(verdict['classification'], ('FAIL', 'INVALID_TEST_EXECUTION'))
        self.assertTrue(verdict['formal_request_attempted'])
        self.assertEqual(verdict['formal_request_sent'], transport['formal_request_sent'])
        self.assertEqual(attempt['maximum_attempts'], 1)
        self.assertEqual(attempt['attempt_number'], 1)
        self.assertTrue(attempt['formal_request_attempted'])
        return verdict, transport

    def test_initial_builder_uses_verified_producer_asset_in_consumer_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            execution.install_value = wiring.surface(execution.identity, [])
            with patch.object(execution, 'py', wraps=execution.py) as call:
                execution.prepare()
            self.assertEqual(call.call_args.args[1], wiring.HERE / 'prepare_issue55_stage3_fixture.py')
            self.assertEqual(execution.program.parent, execution.consumer)
            self.assertTrue(all(not row['exists'] for row in execution.before.values()))
            self.assertEqual(len(execution.initial['input_hashes']), 3)
            self.assertEqual(wiring.jq(execution.out / 'initial-builder.json', '.status'), 'ok')

    def test_missing_initial_builder_stops_before_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            execution.install_value = wiring.surface(execution.identity, [])
            with patch.object(wiring, 'HERE', Path(directory)), patch.object(execution, 'py') as call:
                with self.assertRaisesRegex(RuntimeError, '初态构造'):
                    execution.prepare()
            call.assert_not_called()
            self.assertFalse(execution.program.exists())

    def test_install_uses_this_run_product_source_without_version_equality_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='formal', consumer=None,
                product_source='refs/pr73-current')
            execution = wiring.Execution(args)
            with patch.object(execution, 'run', return_value=CompletedProcess([], 0, b'installed', b'')) as run:
                execution.install()
            run.assert_called_once_with('install', ['apm', 'install', '--target', 'codex',
                '--parallel-downloads', '1',
                'ScholarWorkflow/professor-contact#refs/pr73-current'],
                cwd=execution.consumer, required=False)
            evidence = json.loads((execution.out / 'install.json').read_text())
            self.assertEqual(evidence['status'], 'ok')
            self.assertEqual(evidence['requested_product_source'], 'refs/pr73-current')
            self.assertEqual(evidence['product_source_kind'], 'remote_selector')
            self.assertNotIn('product_source_root', evidence)
            self.assertEqual(evidence['checks'][0]['detail']['source_mode'], 'remote_selector')
            self.assertIsNone(evidence['installed_product_versions'])

    def test_installation_check_runs_installed_writer_and_records_exclusive_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.fresh_execution(directory)
            response_bytes = {}

            def fake_subprocess_run(argv, *, cwd, capture_output, timeout, check):
                if argv[0] == 'pwd':
                    return CompletedProcess(argv, 0, b'/workspace\n', b'')
                if argv[0] == 'apm':
                    script = Path(cwd) / '.agents/skills/professor-contact/scripts/contact_state.py'
                    script.parent.mkdir(parents=True)
                    script.write_text('# installed command test double\n', encoding='utf-8')
                    return CompletedProcess(argv, 0, b'installed', b'')
                if argv[0] == 'python3':
                    result = json.loads(argv[argv.index('--result-json') + 1])
                    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)
                           + '\n').encode('utf-8')
                    target = Path(argv[argv.index('--output-file') + 1])
                    target.write_bytes(raw)
                    target.chmod(0o600)
                    response_bytes['writer'] = raw
                    return CompletedProcess(argv, 0, raw, b'')
                raise AssertionError(f'unexpected command: {argv!r}')

            with patch.object(execution, 'versions'), \
                 patch.object(execution, 'record_provenance'), \
                 patch.object(execution, 'port') as port, \
                 patch.object(execution, 'prepare') as prepare, \
                 patch.object(execution, 'formal') as formal, \
                 patch.object(wiring.subprocess, 'run', side_effect=fake_subprocess_run) as run:
                self.assertEqual(execution.execute(), 0)

            writer_argv = next(call.args[0] for call in run.call_args_list
                               if call.args[0][0] == 'python3')
            self.assertEqual({call.args[0][0] for call in run.call_args_list},
                             {'pwd', 'apm', 'python3'})
            installed_script = execution.consumer / '.agents/skills/professor-contact/scripts/contact_state.py'
            self.assertEqual(Path(writer_argv[1]), installed_script)
            writer = json.loads((execution.out / 'writer.json').read_text())
            call = writer['controlled_call']
            output = call['output']
            self.assertEqual(writer['schema'], 'issue66.writer-observation.v1')
            self.assertEqual(writer['classification'], 'PASS')
            self.assertEqual(call['source'], str(installed_script.resolve()))
            self.assertEqual(call['exit_code'], 0)
            self.assertFalse(output['exists_before'])
            self.assertTrue(output['exists_after'])
            self.assertEqual(output['mode'], '0600')
            self.assertEqual(base64.b64decode(call['stdout_b64']), response_bytes['writer'])
            self.assertEqual(base64.b64decode(output['bytes_b64']), response_bytes['writer'])
            for log_path in call['command_log'].values():
                self.assertTrue((execution.out / log_path).is_file())
            port.assert_not_called()
            prepare.assert_not_called()
            formal.assert_not_called()

    def test_install_failure_is_case_not_started_and_never_calls_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.fresh_execution(directory)

            def fake_subprocess_run(argv, *, cwd, capture_output, timeout, check):
                if argv[0] == 'apm':
                    return CompletedProcess(argv, 128, b'fetch failed', b'TLS EOF')
                return CompletedProcess(argv, 0, b'/workspace\n', b'')

            with patch.object(execution, 'versions'), \
                 patch.object(execution, 'record_provenance'), \
                 patch.object(execution, 'installation_writer_check') as writer_call, \
                 patch.object(execution, 'port') as port, \
                 patch.object(execution, 'prepare') as prepare, \
                 patch.object(execution, 'formal') as formal, \
                 patch.object(wiring.subprocess, 'run', side_effect=fake_subprocess_run):
                self.assertEqual(execution.execute(), 2)

            install = json.loads((execution.out / 'install.json').read_text())
            attempt = install['checks'][0]['detail']
            self.assertEqual(install['status'], 'error')
            self.assertEqual(attempt['exit_code'], 128)
            self.assertEqual(attempt['argv'][0], 'apm')
            self.assertEqual(attempt['command'], shlex.join(attempt['argv']))
            self.assertEqual(base64.b64decode(attempt['stdout_b64']), b'fetch failed')
            self.assertEqual(base64.b64decode(attempt['stderr_b64']), b'TLS EOF')
            self.assertEqual(set(attempt['command_log']), {'metadata', 'stdout', 'stderr'})
            self.assertTrue((execution.out / attempt['command_log']['metadata']).is_file())
            self.assertTrue((execution.out / attempt['command_log']['stdout']).is_file())
            self.assertTrue((execution.out / attempt['command_log']['stderr']).is_file())
            writer = json.loads((execution.out / 'writer.json').read_text())
            verdict = json.loads((execution.out / 'verdict.json').read_text())
            self.assertEqual(writer['classification'], 'CASE_NOT_STARTED')
            self.assertIsNone(writer['controlled_call'])
            self.assertIsNone(writer['save_input'])
            self.assertEqual(verdict['classification'], 'CASE_NOT_STARTED')
            self.assertIsNone(verdict['save_input'])
            writer_call.assert_not_called()
            port.assert_not_called()
            prepare.assert_not_called()
            formal.assert_not_called()

    def test_formal_mode_passes_writer_evidence_to_unique_judge(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.fresh_execution(directory, mode='formal')
            request_value = {'command': 'mock only'}
            request_path = execution.out / 'request.json'
            wiring.write(request_path, request_value)
            execution.before = wiring.snapshot(execution.program)
            fixture = wiring.surface(execution.identity, [])
            wiring.write(execution.out / 'fixture-pre.json', fixture)
            response = {'output': {'thread_id': 'root', 'turn_id': 'turn',
                                   'app_server_events': []}}
            response_raw = (json.dumps(response) + '\n').encode('utf-8')
            judge_calls = []

            def fake_subprocess_run(argv, *, cwd, capture_output, timeout, check):
                if argv[0] != 'curl':
                    raise AssertionError(f'unexpected command: {argv!r}')
                Path(argv[argv.index('--output') + 1]).write_bytes(response_raw)
                uploaded = request_path.stat().st_size
                return CompletedProcess(argv, 0, f'200\t{uploaded}'.encode(), b'')

            def fake_py(name, path, *argv, required=True):
                options = dict(zip(argv[::2], argv[1::2]))
                if name == 'adapter':
                    Path(options['--output']).write_text('{}\n', encoding='utf-8')
                elif name == 'unique-judge':
                    judge_calls.append(argv)
                    Path(options['--output']).write_text(
                        '{"classification":"BLOCKED"}\n', encoding='utf-8')
                else:
                    raise AssertionError(f'unexpected helper: {name}')
                return CompletedProcess([str(path)], 0, b'', b'')

            def fake_jq(path, expression='.'):
                name = Path(path).name
                if name == 'response-raw.json' and expression == '.':
                    return response
                if name == 'response-raw.json':
                    return []
                if name == 'adapter-raw.json':
                    return {'dispatch': {'thread_relations': []}}
                if name == 'fixture-pre.json':
                    return fixture
                if name == 'judge-verdict.json':
                    return {'classification': 'BLOCKED', 'facts': []}
                raise AssertionError(f'unexpected JSON input: {path!r}')

            with patch.object(execution, '_snapshot_writer_handoff_paths', return_value=set()), \
                 patch.object(execution, 'py', side_effect=fake_py), \
                 patch.object(wiring, 'jq', side_effect=fake_jq), \
                 patch.object(wiring.subprocess, 'run', side_effect=fake_subprocess_run):
                self.assertEqual(execution.formal('4312'), 1)

            self.assertEqual(len(judge_calls), 1)
            judge_argv = list(judge_calls[0])
            self.assertEqual(judge_argv.count('--writer-evidence'), 1)
            writer_evidence_path = Path(
                judge_argv[judge_argv.index('--writer-evidence') + 1])
            self.assertEqual(writer_evidence_path, execution.out / 'writer.json')
            writer = json.loads((execution.out / 'writer.json').read_text())
            self.assertEqual(writer['schema'], 'issue66.writer-observation.v1')
            self.assertEqual(writer['evidence_set_id'], execution.identity)
            self.assertEqual(writer['observations'], [])

    def test_absolute_local_project_source_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            source = root / 'local-product'
            source.mkdir()
            (source / 'apm.yml').write_text('name: professor-contact\n', encoding='utf-8')
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                product_source=str(source))
            with patch.object(wiring.Execution, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, '不接受本地路径'):
                    wiring.Execution(args)
            run.assert_not_called()
            self.assertFalse((root / 'evidence').exists())

    def test_relative_local_project_source_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            source = root / 'local-product'
            source.mkdir()
            (source / 'apm.yml').write_text('name: professor-contact\n', encoding='utf-8')
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                product_source='local-product')
            with patch.object(wiring.Path, 'cwd', return_value=root), \
                    patch.object(wiring.Execution, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, '不接受本地路径'):
                    wiring.Execution(args)
            run.assert_not_called()
            self.assertFalse((root / 'evidence').exists())

    def test_existing_relative_local_path_is_rejected_even_without_apm_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            (root / 'local-data').mkdir()
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                product_source='local-data')
            with patch.object(wiring.Path, 'cwd', return_value=root), \
                    patch.object(wiring.Execution, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, '不接受本地路径'):
                    wiring.Execution(args)
            run.assert_not_called()
            self.assertFalse((root / 'evidence').exists())

    def test_windows_relative_path_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                product_source='local\\product')
            with patch.object(wiring.Execution, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, '不接受本地路径'):
                    wiring.Execution(args)
            run.assert_not_called()
            self.assertFalse((root / 'evidence').exists())

    def test_dot_relative_and_file_url_sources_are_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            for source in ('./local-product', 'file:///tmp/local-product'):
                with self.subTest(source=source):
                    args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                        evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                        product_source=source)
                    with patch.object(wiring.Execution, 'run') as run:
                        with self.assertRaisesRegex(RuntimeError, '不接受本地路径'):
                            wiring.Execution(args)
                    run.assert_not_called()
                    self.assertFalse((root / 'evidence').exists())

    def test_symlink_product_source_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as directory:
            from argparse import Namespace
            root = Path(directory)
            source = root / 'local-product'
            source.mkdir()
            (source / 'apm.yml').write_text('name: professor-contact\n', encoding='utf-8')
            link = root / 'product-link'
            link.symlink_to(source, target_is_directory=True)
            args = Namespace(repository=str(PATH.parents[5]), fixture_root=directory,
                evidence_dir=str(root / 'evidence'), mode='preflight', consumer=None,
                product_source='product-link')
            with patch.object(wiring.Path, 'cwd', return_value=root), \
                    patch.object(wiring.Execution, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, '不接受符号链接'):
                    wiring.Execution(args)
            run.assert_not_called()
            self.assertFalse((root / 'evidence').exists())

    def test_source_revision_and_dirty_status_are_recorded_without_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            (execution.out / 'versions.json').write_text('{"uv":"uv actual"}')
            failed = CompletedProcess(['git'], 128, b'', b'not a git checkout')
            with patch.object(execution, 'run', return_value=failed), \
                 patch.object(wiring, 'jq', return_value={'uv': 'uv actual'}):
                execution.record_provenance()
            record = json.loads((execution.out / 'provenance.json').read_text())
            self.assertEqual(record['product_source_input'], 'refs/pr73-current')
            self.assertEqual(record['product_source_kind'], 'remote_selector')
            self.assertNotIn('product_source_root', record)
            self.assertIsNone(record['test_source']['head']['value'])
            self.assertEqual(record['test_source']['worktree_status']['exit_code'], 128)

    def test_credential_observation_rejects_symlink_before_resolving(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            target = execution.consumer / 'actual.json'
            target.write_text('{}')
            link = execution.consumer / 'link.json'
            link.symlink_to(target)
            capture = {'invocation_file': str(link), 'invocation_sha256': wiring.digest(b'{}')}
            with patch.object(wiring, 'jq', return_value=[capture]):
                with self.assertRaisesRegex(RuntimeError, '普通文件'):
                    execution.credential_observation()

    def test_dynamic_trust_key_and_consensus_configuration(self):
        argv = shlex.split(wiring.request(Path('/tmp/consumer.a b'), Path('/tmp/program'))['command'])
        self.assertIn('projects={"/tmp/consumer.a b"={trust_level="trusted"}}', argv)
        self.assertNotIn('--profile', argv)
        self.assertEqual(argv[argv.index('--model') + 1], 'gpt-6-luna')
        self.assertEqual(argv[argv.index('--sandbox') + 1], 'workspace-write')

    def test_actual_snapshot_detects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(all(not row['exists'] for row in wiring.snapshot(root).values()))
            path = root / wiring.ARTIFACTS['套磁想法候选.md']
            path.parent.mkdir(parents=True)
            path.write_bytes(b'first')
            before = wiring.snapshot(root)
            path.write_bytes(b'changed')
            self.assertNotEqual(before, wiring.snapshot(root))

    def test_history_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'evidence.json'
            wiring.write(target, {'actual': 1})
            with self.assertRaises(FileExistsError):
                wiring.write(target, {'actual': 2})
            self.assertEqual(wiring.jq(target, '.actual'), 1)

    def test_missing_relation_surface_is_invalid(self):
        result = wiring.topology('run', {'output':{'thread_id':'root'}}, {}, {}, {}, {})
        self.assertEqual(result['status'], 'invalid')

    def test_formal_owners_use_sender_and_preserve_conflicts(self):
        relation = lambda sender: {'tool':'spawnAgent','status':'completed',
            'sender_thread_id':sender,'parent_thread_id':'diagnostic','receiver_thread_ids':['child']}
        result = wiring.topology('run', {'output':{'thread_id':'root'}},
            {'dispatch':{'thread_relations':[relation('root'),relation('other')]}}, {}, {}, {})
        self.assertEqual(result['classification'], 'INVALID_TEST_EXECUTION')

    def test_partial_topology_does_not_require_future_children(self):
        result = wiring.topology('run', {'output':{'thread_id':'root'}},
            {'dispatch':{'thread_relations':[]}}, {}, {}, {})
        self.assertEqual(result['classification'], 'PASS')
        self.assertEqual(result['root_direct_spawn_child_ids'], [])
        # 局部拓扑报告不负责业务是否委派；唯一判定仍会拒绝完整运行零委派。

    def test_preflight_never_checks_remote_approval_or_sends_request(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(repository=str(PATH.parents[5]),fixture_root=directory,
                evidence_dir=str(Path(directory)/'new'),mode='preflight',consumer=None,
                product_source='refs/pr73-current')
            execution = wiring.Execution(args)
            service = Mock()
            execution.service = service
            with patch.object(execution,'run'), patch.object(execution,'versions'), \
                 patch.object(execution,'record_provenance'), patch.object(execution,'port') as port, \
                 patch.object(execution,'service') as service, patch.object(execution,'install'), \
                 patch.object(execution,'prepare'), patch.object(execution,'formal') as formal:
                self.assertEqual(execution.execute(),0)
                port.assert_not_called()
                formal.assert_not_called()
            service.assert_not_called()

    def test_eval_port_lookup_runs_from_repository_worktree(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            with patch.object(execution, 'run', return_value=CompletedProcess(
                    [], 0, b'4312\n', b'')) as run:
                self.assertEqual(execution.port(), '4312')
            run.assert_called_once_with('eval-port', [
                'direnv', 'exec', '.', 'printenv', 'EVAL_PORT'])
            self.assertEqual(execution.repo, PATH.parents[5].resolve())

    def test_transport_failure_before_body_upload_is_case_not_started(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.formal_execution(directory)
            with patch.object(execution, 'run', return_value=CompletedProcess(
                    ['curl'], 56, b'000\t0', b'connection ended before upload')) as run:
                self.assertEqual(execution.formal('4312'), 2)
            run.assert_called_once()
            verdict, transport = self.assert_transport_terminal(execution, 'CASE_NOT_STARTED')
            self.assertFalse(verdict['formal_request_sent'])
            self.assertEqual(transport['request_body_uploaded_bytes'], 0)
            self.assertFalse(transport['http_response_received'])

    def test_curl_process_not_started_is_case_not_started(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.formal_execution(directory)
            with patch.object(execution, 'run', side_effect=wiring.CommandNotStarted(
                    'curl could not start')) as run:
                self.assertEqual(execution.formal('4312'), 2)
            run.assert_called_once()
            verdict, transport = self.assert_transport_terminal(execution, 'CASE_NOT_STARTED')
            self.assertFalse(transport['curl_process_started'])
            self.assertEqual(transport['request_body_uploaded_bytes'], 0)
            self.assertFalse(transport['http_response_received'])
            self.assertIn('transport_error', transport)

    def test_transport_failure_after_body_upload_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.formal_execution(directory)
            expected = (execution.out / 'request.json').stat().st_size
            with patch.object(execution, 'run', return_value=CompletedProcess(
                    ['curl'], 56, f'000\t{expected}'.encode(), b'connection ended after upload')) as run:
                self.assertEqual(execution.formal('4312'), 2)
            run.assert_called_once()
            verdict, transport = self.assert_transport_terminal(execution, 'BLOCKED')
            self.assertTrue(verdict['formal_request_sent'])
            self.assertEqual(transport['request_body_uploaded_bytes'], expected)
            self.assertFalse(transport['http_response_received'])
            # 与零上传反例仅改变上传字节数，传输失败仍不能变成产品失败或无效执行。
            self.assertEqual(wiring._transport_classification(56, None, 0, expected),
                             'CASE_NOT_STARTED')
            self.assertEqual(wiring._transport_classification(56, None, expected, expected),
                             'BLOCKED')

    def test_http_non_success_is_blocked_and_retains_status(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.formal_execution(directory)
            with patch.object(execution, 'run', return_value=CompletedProcess(
                    ['curl'], 0, b'503\t0', b'')) as run:
                self.assertEqual(execution.formal('4312'), 2)
            run.assert_called_once()
            verdict, transport = self.assert_transport_terminal(execution, 'BLOCKED')
            self.assertEqual(verdict['http_status'], 503)
            self.assertEqual(transport['http_status_raw'], '503')
            self.assertTrue(transport['http_response_received'])

    def test_unparseable_upload_is_blocked_conservatively(self):
        with tempfile.TemporaryDirectory() as directory:
            execution = self.formal_execution(directory)
            with patch.object(execution, 'run', return_value=CompletedProcess(
                    ['curl'], 56, b'000\tunknown', b'connection ended')) as run:
                self.assertEqual(execution.formal('4312'), 2)
            run.assert_called_once()
            verdict, transport = self.assert_transport_terminal(execution, 'BLOCKED')
            self.assertIsNone(verdict['formal_request_sent'])
            self.assertIsNone(transport['request_body_uploaded_bytes'])
            self.assertFalse(transport['http_response_received'])
