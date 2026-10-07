"""把专用临时传递位置绑定到实际请求。"""
import hashlib
import json
import shlex
from pathlib import Path


DECLARATION_SCHEMA = "issue-68-transfer-location-binding-v1"
REQUEST_ARTIFACT = "codex/codex-request.json"
DECLARATION_ARTIFACT = "codex/transfer-location-declaration.txt"
BUSINESS_PROMPT_ARTIFACT = "codex/business-prompt.txt"
MANIFEST_ARTIFACT = "codex/fixture-manifest.request.json"


def _overlaps(left, right):
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def validate_location_root(path, protected_roots):
    """要求目录已存在且为空，并与所有受保护目录分开。"""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("transfer_location_root_must_be_absolute")
    if path.is_symlink():
        raise ValueError("transfer_location_root_must_not_be_symlink")
    try:
        root = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("transfer_location_root_missing") from exc
    if not root.is_dir():
        raise ValueError("transfer_location_root_not_directory")
    if any(root.iterdir()):
        raise ValueError("transfer_location_root_not_empty")
    for label, protected in protected_roots.items():
        protected = Path(protected).resolve()
        if _overlaps(root, protected):
            raise ValueError("transfer_location_root_overlaps_protected_root:" + str(label))
    return root


def location_declaration(root):
    """只生成位置说明，业务提示词单独保存。"""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("transfer_location_root_must_be_absolute")
    return (f"本次请求的唯一临时传递位置为：{root}。"
            "根任务必须将此位置转告负责该教授的代理。文件名和目录布局由产品自行选择。")


def compose_prompt(declaration, business_prompt):
    if not isinstance(declaration, str) or not declaration.strip():
        raise ValueError("transfer_location_declaration_missing")
    if not isinstance(business_prompt, str) or not business_prompt:
        raise ValueError("transfer_business_prompt_missing")
    return declaration + "\n\n" + business_prompt


def save_request_prompts(root, business_prompt, evidence_directory):
    """分别保存原业务提示词和位置说明，并返回实际请求文本。"""
    declaration = location_declaration(root)
    combined = compose_prompt(declaration, business_prompt)
    directory = Path(evidence_directory)
    (directory / "transfer-location-declaration.txt").write_text(
        declaration, encoding="utf-8")
    (directory / "business-prompt.txt").write_text(
        business_prompt, encoding="utf-8")
    return {
        "declaration": declaration,
        "business_prompt": business_prompt,
        "combined_prompt": combined,
    }


def bind_lifecycle_observation(manifest, root):
    """把同一个规范路径加入请求前后的生命周期观察范围。"""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("transfer_location_root_must_be_absolute")
    root_text = str(root.resolve())
    roots = manifest.get("lifecycle_extra_observation_roots", [])
    if not isinstance(roots, list):
        raise ValueError("lifecycle_extra_observation_roots_invalid")
    normalized = [str(Path(item).resolve()) for item in roots]
    if normalized.count(root_text) > 1:
        raise ValueError("transfer_location_root_observation_duplicated")
    if root_text not in normalized:
        roots.append(root_text)
    manifest["lifecycle_extra_observation_roots"] = roots
    manifest["transfer_location_root"] = root_text
    return manifest


def request_binding_record(root, declaration, business_prompt, request_path, manifest_path,
                           request_artifact=REQUEST_ARTIFACT, request_body_sha256=None):
    """把实际请求字节摘要绑定到单独保存的位置说明和业务提示词。"""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("transfer_location_root_must_be_absolute")
    request_path = Path(request_path)
    manifest_path = Path(manifest_path)
    try:
        request_bytes = request_path.read_bytes()
        request = json.loads(request_bytes.decode("utf-8"))
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        command = request.get("command")
        if not isinstance(command, str):
            raise ValueError("command")
        argv = shlex.split(command)
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError, ValueError) as exc:
        raise ValueError("transfer_request_artifact_invalid") from exc
    combined_prompt = compose_prompt(declaration, business_prompt)
    if declaration != location_declaration(root):
        raise ValueError("transfer_location_declaration_mismatch")
    if not argv or argv[-1] != combined_prompt:
        raise ValueError("transfer_request_prompt_mismatch")
    root_text = str(root.resolve())
    lifecycle_roots = manifest.get("lifecycle_extra_observation_roots")
    owner_capture = manifest.get("owner_capture")
    if manifest.get("transfer_location_root") != root_text or \
            not isinstance(lifecycle_roots, list) or lifecycle_roots.count(root_text) != 1 or \
            not isinstance(owner_capture, dict) or \
            owner_capture.get("manifest_path") != str((manifest_path.parent / "fixture-manifest.json").resolve()) or \
            manifest.get("transfer_location_manifest_snapshot") != str(manifest_path.resolve()):
        raise ValueError("transfer_location_manifest_binding_mismatch")
    if request_body_sha256 is not None and (not isinstance(request_body_sha256, str)
                                              or len(request_body_sha256) != 64):
        raise ValueError("transfer_request_body_digest_invalid")
    record = {
        "schema": DECLARATION_SCHEMA,
        "transfer_location_root": root_text,
        "declaration_artifact": DECLARATION_ARTIFACT,
        "declaration_sha256": hashlib.sha256(declaration.encode("utf-8")).hexdigest(),
        "business_prompt_artifact": BUSINESS_PROMPT_ARTIFACT,
        "business_prompt_sha256": hashlib.sha256(business_prompt.encode("utf-8")).hexdigest(),
        "combined_prompt_sha256": hashlib.sha256(combined_prompt.encode("utf-8")).hexdigest(),
        "request_artifact": {
            "path": request_artifact,
            "sha256": hashlib.sha256(request_bytes).hexdigest(),
        },
        "manifest_artifact": {
            "path": MANIFEST_ARTIFACT,
            "filesystem_path": str(manifest_path.resolve()),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
    }
    if request_body_sha256 is not None:
        record["request_body_sha256"] = request_body_sha256
    return record
