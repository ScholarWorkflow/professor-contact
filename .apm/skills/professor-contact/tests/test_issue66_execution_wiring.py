"""确定性接线检查；不连接评测服务。"""
import importlib.util
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).parent / 'runtime/issue66_execution.py'
spec = importlib.util.spec_from_file_location('issue66_execution', PATH)
wiring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wiring)


class ExecutionWiringTests(unittest.TestCase):
    def execution(self, directory):
        from argparse import Namespace
        root = Path(directory)
        consumer = root / 'consumer'
        consumer.mkdir()
        return wiring.Execution(Namespace(repository=str(PATH.parents[5]),
            fixture_root=str(root), evidence_dir=str(root / 'evidence'),
            mode='installation-check', consumer=str(consumer),
            frozen_manifest=None, service_contract=None))

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

    def test_initial_builder_source_mismatch_stops_before_prepare(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as directory:
            execution = self.execution(directory)
            execution.install_value = wiring.surface(execution.identity, [])
            with patch.object(execution, 'run', return_value=CompletedProcess([], 0, b'wrong', b'')), \
                 patch.object(execution, 'py') as call:
                with self.assertRaisesRegex(RuntimeError, '初态构造'):
                    execution.prepare()
            call.assert_not_called()
            self.assertFalse(execution.program.exists())

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

    def test_preflight_never_checks_approval_or_sends_request(self):
        from argparse import Namespace
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(repository=str(PATH.parents[5]),fixture_root=directory,
                evidence_dir=str(Path(directory)/'new'),mode='preflight',consumer=None,
                frozen_manifest=None,service_contract=None)
            execution = wiring.Execution(args)
            with patch.object(execution,'run'), patch.object(execution,'versions'), \
                 patch.object(execution,'verify_versions'), patch.object(execution,'port',return_value='1234'), \
                 patch.object(execution,'service'), patch.object(execution,'install'), \
                 patch.object(execution,'prepare'), patch.object(execution,'formal') as formal, \
                 patch.object(execution,'unlock') as unlock:
                self.assertEqual(execution.execute(),0)
                formal.assert_not_called()
                unlock.assert_not_called()
