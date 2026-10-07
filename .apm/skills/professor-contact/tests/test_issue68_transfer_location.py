"""第 68 号问题的临时传递位置请求绑定测试。"""
import hashlib
import contextlib
import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock


RUNTIME = Path(__file__).resolve().parent / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import build_issue68_codex_request_r12 as request_builder
import issue68_transfer_location as transfer_location
import run_issue68_stage5_routing_r19_codex as entry


class TestIssue68TransferLocation(unittest.TestCase):
    def prepare_fake_approval_config(self, consumer, _fixture_root, evidence_path):
        values = {
            "approval_policy": "on-request",
            "approvals_reviewer": "auto_review",
        }
        config_path = Path(consumer) / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            'approval_policy = "on-request"\napprovals_reviewer = "auto_review"\n',
            encoding="utf-8")
        record = {"status": "PREPARED", "values": values}
        entry.base.write_json(evidence_path, record)
        return record

    def verify_fake_approval_config(self, consumer, setup_path, evidence_path,
                                    _setup_artifact):
        values = {
            "approval_policy": "on-request",
            "approvals_reviewer": "auto_review",
        }
        self.assertTrue(Path(setup_path).is_file())
        config_path = Path(consumer) / ".codex" / "config.toml"
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual({key: config.get(key) for key in values}, values)
        record = {
            "status": "PRESERVED",
            "requested_values": values,
            "observed_values": values,
            "statuses": {key: "MATCH" for key in values},
            "config_sha256_after_install": hashlib.sha256(
                config_path.read_bytes()).hexdigest(),
        }
        entry.base.write_json(evidence_path, record)
        return record

    def test_valid_root_prompt_and_request_are_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "request-transfer"
            root.mkdir()
            consumer = temp / "consumer"
            consumer.mkdir()
            business_prompt = "请按本次业务要求处理合成输入。"

            validated = transfer_location.validate_location_root(root, {})
            prompt_materials = transfer_location.save_request_prompts(
                validated, business_prompt, temp)
            declaration = prompt_materials["declaration"]
            combined = prompt_materials["combined_prompt"]
            self.assertEqual((temp / "transfer-location-declaration.txt").read_text(encoding="utf-8"),
                             declaration)
            self.assertEqual((temp / "business-prompt.txt").read_text(encoding="utf-8"),
                             business_prompt)
            request = request_builder.build_request(consumer, combined)
            request_path = temp / "codex-request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
            manifest_path = temp / "fixture-manifest.request.json"
            manifest = {
                "transfer_location_root": str(validated),
                "lifecycle_extra_observation_roots": [str(validated)],
                "owner_capture": {"manifest_path": str((temp / "fixture-manifest.json").resolve())},
                "transfer_location_manifest_snapshot": str(manifest_path.resolve()),
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")

            binding = transfer_location.request_binding_record(
                validated, declaration, business_prompt, request_path, manifest_path)

            self.assertEqual(binding["transfer_location_root"], str(root.resolve()))
            self.assertEqual(binding["declaration_sha256"],
                             hashlib.sha256(declaration.encode("utf-8")).hexdigest())
            self.assertEqual(binding["business_prompt_sha256"],
                             hashlib.sha256(business_prompt.encode("utf-8")).hexdigest())
            self.assertEqual(binding["combined_prompt_sha256"],
                             hashlib.sha256(combined.encode("utf-8")).hexdigest())
            self.assertEqual(binding["request_artifact"]["sha256"],
                             hashlib.sha256(request_path.read_bytes()).hexdigest())
            self.assertEqual(binding["request_artifact"]["path"], "codex/codex-request.json")
            self.assertEqual(binding["manifest_artifact"]["path"],
                             "codex/fixture-manifest.request.json")
            self.assertEqual(binding["manifest_artifact"]["sha256"],
                             hashlib.sha256(manifest_path.read_bytes()).hexdigest())
            self.assertEqual(binding["declaration_artifact"],
                             "codex/transfer-location-declaration.txt")
            self.assertEqual(binding["business_prompt_artifact"], "codex/business-prompt.txt")
            self.assertIn(declaration, request["command"])
            self.assertIn(business_prompt, request["command"])
            self.assertIn("根任务必须将此位置转告负责该教授的代理", declaration)
            self.assertIn("文件名和目录布局由产品自行选择", declaration)
            self.assertNotIn("教授甲", declaration)
            self.assertNotIn("选择答案", declaration)

    def test_lifecycle_root_is_bound_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "request-transfer"
            root.mkdir()
            manifest = {"lifecycle_extra_observation_roots": []}

            transfer_location.bind_lifecycle_observation(manifest, root)
            transfer_location.bind_lifecycle_observation(manifest, root)

            self.assertEqual(manifest["transfer_location_root"], str(root.resolve()))
            self.assertEqual(manifest["lifecycle_extra_observation_roots"], [str(root.resolve())])

    def test_codex_request_wrapper_saves_and_sends_location_declaration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            output = temp / "output"
            output.mkdir()
            root = temp / "request-transfer"
            root.mkdir()
            directory = output / "codex"
            consumer = output / "consumers" / "codex"
            script = consumer / ".apm" / "skills" / "professor-contact" / "scripts" / "contact_state.py"
            config_path = consumer / ".codex" / "config.toml"
            approval_values = {
                "approval_policy": "on-request",
                "approvals_reviewer": "auto_review",
            }
            approval_callback_order = []

            def prepare_approval_config(request_consumer, _fixture_root, evidence_path):
                self.assertEqual(request_consumer, consumer)
                self.assertFalse(config_path.exists())
                config_path.parent.mkdir(parents=True)
                config_path.write_text(
                    'approval_policy = "on-request"\napprovals_reviewer = "auto_review"\n',
                    encoding="utf-8")
                record = {"status": "PREPARED", "values": approval_values}
                entry.base.write_json(evidence_path, record)
                approval_callback_order.append("before_codex_install")
                return record

            def verify_approval_config(request_consumer, setup_path, evidence_path,
                                      setup_artifact):
                self.assertEqual(request_consumer, consumer)
                self.assertTrue(Path(setup_path).is_file())
                self.assertEqual(setup_artifact,
                                 "codex/project-approval-config-setup.json")
                config = tomllib.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual({key: config.get(key) for key in approval_values},
                                 approval_values)
                self.assertIn("synthetic", config["mcp_servers"])
                record = {
                    "status": "PRESERVED",
                    "requested_values": approval_values,
                    "observed_values": approval_values,
                    "statuses": {key: "MATCH" for key in approval_values},
                    "config_sha256_after_install": "synthetic-config-sha256",
                }
                entry.base.write_json(evidence_path, record)
                approval_callback_order.append("after_codex_install")
                return record

            def install_host(_args, run_output, _host, *,
                             before_codex_install=None, after_codex_install=None):
                self.assertEqual(run_output, output)
                directory.mkdir()
                consumer.mkdir(parents=True)
                if before_codex_install is not None:
                    before_codex_install(consumer, directory)
                approval_callback_order.append("apm_install")
                with config_path.open("a", encoding="utf-8") as config_file:
                    config_file.write(
                        '\n[mcp_servers.synthetic]\ncommand = "synthetic"\n')
                program_root = consumer / "program"
                program_root.mkdir()
                script.parent.mkdir(parents=True)
                script.write_text("synthetic installed entrypoint", encoding="utf-8")
                (directory / "root-prompt.txt").write_text("合成业务提示。", encoding="utf-8")
                manifest = {"program_root": str(program_root),
                            "lifecycle_extra_observation_roots": []}
                entry.base.write_json(directory / "fixture-manifest.json", manifest)
                if after_codex_install is not None:
                    after_codex_install(consumer, directory)
                return directory, consumer, manifest

            def codex_host(args, run_output):
                request_dir, request_consumer, _manifest = entry.base.install_host(
                    args, run_output, "codex")
                prompt = (request_dir / "root-prompt.txt").read_text(encoding="utf-8")
                return entry.base.build_request(request_consumer, prompt)

            args = type("Args", (), {
                "transfer_location_root": root.resolve(),
                "fixture_root": temp / "fixture-root",
            })()
            preflight = {"runtime_environment_facts": {}, "runtime_environment_evidence": {}}
            runtime_record = {
                "runtime_environment_facts": {},
                "runtime_environment_evidence": {},
                "request_artifact": {"path": "codex/codex-request.json", "sha256": "synthetic"},
            }
            with mock.patch.object(
                    transfer_location, "validate_location_root",
                    wraps=transfer_location.validate_location_root) as validate_root, \
                    mock.patch.object(entry.base, "install_host", side_effect=install_host), \
                    mock.patch.object(entry.base, "codex_host", side_effect=codex_host), \
                    mock.patch.object(entry, "prepare_project_approval_configuration",
                                      side_effect=prepare_approval_config), \
                    mock.patch.object(entry, "verify_project_approval_configuration_after_install",
                                      side_effect=verify_approval_config), \
                    mock.patch.object(entry, "_record_request_runtime_facts",
                                      return_value=runtime_record):
                request = entry._codex_host_with_runtime_capture(
                    args, output, preflight, {}, {}, {}, {})

            self.assertEqual(validate_root.call_count, 1)
            self.assertEqual(approval_callback_order, [
                "before_codex_install", "apm_install", "after_codex_install"])
            self.assertTrue((directory / "project-approval-config-setup.json").is_file())
            self.assertTrue((directory / "project-approval-config-install-check.json").is_file())
            validated_path, protected_roots = validate_root.call_args.args
            self.assertEqual(validated_path, root.resolve())
            self.assertEqual(set(protected_roots), {"consumer", "program", "evidence_output"})
            self.assertEqual(Path(protected_roots["consumer"]).resolve(), consumer.resolve())
            self.assertEqual(Path(protected_roots["program"]).resolve(),
                             (consumer / "program").resolve())
            self.assertEqual(Path(protected_roots["evidence_output"]).resolve(), output.resolve())

            declaration = transfer_location.location_declaration(root.resolve())
            business_prompt = "合成业务提示。"
            self.assertIn(declaration, request["command"])
            self.assertIn(business_prompt, request["command"])
            self.assertEqual((directory / "transfer-location-declaration.txt").read_text(encoding="utf-8"),
                             declaration)
            self.assertEqual((directory / "business-prompt.txt").read_text(encoding="utf-8"),
                             business_prompt)
            saved_manifest = json.loads((directory / "fixture-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["lifecycle_extra_observation_roots"], [str(root.resolve())])
            binding = json.loads((directory / "transfer-location-binding.json").read_text(encoding="utf-8"))
            self.assertEqual(binding["transfer_location_root"], str(root.resolve()))
            self.assertEqual(binding["request_artifact"]["sha256"],
                             hashlib.sha256((directory / "codex-request.json").read_bytes()).hexdigest())
            manifest_snapshot = directory / "fixture-manifest.request.json"
            self.assertEqual(binding["manifest_artifact"]["sha256"],
                             hashlib.sha256(manifest_snapshot.read_bytes()).hexdigest())
            request_manifest = json.loads(manifest_snapshot.read_text(encoding="utf-8"))
            self.assertEqual(request_manifest["transfer_location_root"], str(root.resolve()))

    def test_rejects_non_absolute_root(self):
        with self.assertRaisesRegex(ValueError, "transfer_location_root_must_be_absolute"):
            transfer_location.validate_location_root(Path("relative-transfer"), {})

    def test_rejects_symbolic_link_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            target = temp / "target"
            target.mkdir()
            link = temp / "transfer-link"
            link.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "transfer_location_root_must_not_be_symlink"):
                transfer_location.validate_location_root(link, {})

    def test_rejects_missing_and_non_directory_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "transfer_location_root_missing"):
                transfer_location.validate_location_root(temp / "missing", {})

            file_path = temp / "file"
            file_path.write_text("synthetic", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "transfer_location_root_not_directory"):
                transfer_location.validate_location_root(file_path, {})

    def test_rejects_non_empty_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "transfer"
            root.mkdir()
            (root / "existing.txt").write_text("synthetic", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "transfer_location_root_not_empty"):
                transfer_location.validate_location_root(root, {})

    def test_rejects_overlap_with_each_protected_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for label in ("product", "shared_assets", "service", "evidence_output"):
                with self.subTest(label=label):
                    protected = temp / label
                    protected.mkdir()
                    nested = protected / "transfer"
                    nested.mkdir()

                    with self.assertRaisesRegex(ValueError, "transfer_location_root_overlaps_protected_root"):
                        transfer_location.validate_location_root(nested, {label: protected})

    def test_rejects_request_that_does_not_contain_both_prompt_parts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "request-transfer"
            root.mkdir()
            request_path = temp / "codex-request.json"
            request_path.write_text(json.dumps({"command": "codex -- prompt mismatch"}),
                                    encoding="utf-8")
            manifest_path = temp / "fixture-manifest.request.json"
            manifest_path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "transfer_request_prompt_mismatch"):
                transfer_location.request_binding_record(
                    root, transfer_location.location_declaration(root), "业务提示",
                    request_path, manifest_path)

    def test_rechecks_location_after_install_against_each_protected_root(self):
        for blocked_by in ("consumer", "program", "evidence_output"):
            with self.subTest(blocked_by=blocked_by), tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                output = temp / "evidence"
                output.mkdir()
                consumer = temp / "consumer"
                consumer.mkdir()
                program_root = temp / "program"
                program_root.mkdir()
                protected = {
                    "consumer": consumer,
                    "program": program_root,
                    "evidence_output": output,
                }[blocked_by]
                root = protected / "transfer"
                root.mkdir()
                directory = output / "codex"
                directory.mkdir()

                args = type("Args", (), {
                    "transfer_location_root": root.resolve(),
                    "fixture_root": temp / "fixture-root",
                })()

                def install_host(_args, _run_output, _host, *,
                                 before_codex_install=None, after_codex_install=None):
                    if before_codex_install is not None:
                        before_codex_install(consumer, directory)
                    if after_codex_install is not None:
                        after_codex_install(consumer, directory)
                    return directory, consumer, {
                        "program_root": str(program_root),
                        "lifecycle_extra_observation_roots": [],
                    }

                def codex_host(request_args, run_output):
                    return entry.base.install_host(request_args, run_output, "codex")

                with mock.patch.object(entry.base, "install_host", side_effect=install_host), \
                        mock.patch.object(entry.base, "codex_host", side_effect=codex_host), \
                        mock.patch.object(
                            entry, "prepare_project_approval_configuration",
                            side_effect=self.prepare_fake_approval_config), \
                        mock.patch.object(
                            entry, "verify_project_approval_configuration_after_install",
                            side_effect=self.verify_fake_approval_config):
                    with self.assertRaisesRegex(
                            ValueError,
                            "transfer_location_root_overlaps_protected_root:" + blocked_by):
                        entry._codex_host_with_runtime_capture(
                            args, output, {}, {}, {}, {}, {})

    def test_formal_entry_requires_explicit_transfer_location_argument(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    entry.parse_args([
                        "--producer-root", str(temp / "product"),
                        "--producer-sha", "synthetic-product-revision",
                        "--fixture-root", str(temp / "shared-assets"),
                        "--fixture-sha", "synthetic-assets-revision",
                        "--eval-direnv-root", str(temp / "service"),
                        "--output-dir", str(temp / "evidence"),
                    ])


if __name__ == "__main__":
    unittest.main()
