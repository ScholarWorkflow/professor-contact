#!/usr/bin/env python3
"""Build the fixed, local request artifact for issue #68 PC68-R1.

This utility only prepares files. It never contacts the evaluation service.
Project model and reasoning settings are loaded from the trusted consumer
configuration; the generated command adds only the consumer trust setting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import tempfile
from pathlib import Path


DEFAULT_PROMPT_TEMPLATE = Path(__file__).resolve().parent / "prompts" / "issue68-stage5-root.txt"
PROMPT_TOKEN = "<PC68_PROGRAM>"
PROMPT_TEMPLATE_SHA256 = "2da8b43fe99f0d4481046bd13020f74374a90b155704b861cbd14eb86205f153"
TIMEOUT = 900
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


class RequestBuildError(RuntimeError):
    pass


def _resolved_dir(value: Path, name: str) -> Path:
    path = Path(value).resolve()
    if not path.is_dir():
        raise RequestBuildError(f"{name} is not an existing directory: {path}")
    return path


def _resolved_output(value: Path, name: str) -> Path:
    path = Path(value).resolve()
    if path.is_relative_to(REPOSITORY_ROOT):
        raise RequestBuildError(f"{name} must be outside the repository: {path}")
    return path


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content)
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def build_request(
    *,
    consumer_root: Path,
    program_root: Path,
    template_copy: Path,
    rendered_prompt: Path,
    hash_file: Path,
    output: Path,
    prompt_template: Path = DEFAULT_PROMPT_TEMPLATE,
) -> dict[str, object]:
    consumer = _resolved_dir(consumer_root, "consumer root")
    program = _resolved_dir(program_root, "program root")
    try:
        program.relative_to(consumer)
    except ValueError as exc:
        raise RequestBuildError("program root must be inside the consumer root") from exc

    template_path = Path(prompt_template).resolve()
    try:
        template_bytes = template_path.read_bytes()
    except OSError as exc:
        raise RequestBuildError(f"cannot read prompt template: {template_path}") from exc
    template_hash = hashlib.sha256(template_bytes).hexdigest()
    if template_hash != PROMPT_TEMPLATE_SHA256:
        raise RequestBuildError("prompt template differs from the frozen issue 68 prompt")
    try:
        template = template_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RequestBuildError("prompt template is not valid UTF-8") from exc
    if template.count(PROMPT_TOKEN) != 1:
        raise RequestBuildError("prompt template must contain exactly one program-root token")

    rendered = template.replace(PROMPT_TOKEN, str(program))
    if PROMPT_TOKEN in rendered:
        raise RequestBuildError("rendered prompt still contains the program-root token")
    rendered_bytes = rendered.encode("utf-8")
    rendered_hash = hashlib.sha256(rendered_bytes).hexdigest()

    template_output = _resolved_output(template_copy, "template copy")
    prompt_output = _resolved_output(rendered_prompt, "rendered prompt")
    hashes_output = _resolved_output(hash_file, "hash file")
    request_output = _resolved_output(output, "request file")
    outputs = (template_output, prompt_output, hashes_output, request_output)
    if len(set(outputs)) != len(outputs):
        raise RequestBuildError("template, prompt, hash and request outputs must be distinct")

    trust_override = (
        "projects={" + json.dumps(str(consumer), ensure_ascii=False)
        + '={trust_level="trusted"}}'
    )
    argv = [
        "--json", "--skip-git-repo-check",
        "--sandbox", "workspace-write", "--cd", str(consumer),
        "--config", trust_override,
        "--", rendered,
    ]
    request = {"command": shlex.join(argv), "timeout": TIMEOUT}
    request_bytes = (json.dumps(request, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    hashes_bytes = (
        f"template {template_hash}\nrendered {rendered_hash}\n"
    ).encode("ascii")

    _atomic_write(template_output, template_bytes)
    _atomic_write(prompt_output, rendered_bytes)
    _atomic_write(hashes_output, hashes_bytes)
    _atomic_write(request_output, request_bytes)
    return {
        "request": request,
        "template_sha256": template_hash,
        "rendered_sha256": rendered_hash,
        "outputs": {
            "template": str(template_output),
            "prompt": str(prompt_output),
            "hashes": str(hashes_output),
            "request": str(request_output),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--template-copy", type=Path, required=True)
    parser.add_argument("--rendered-prompt", type=Path, required=True)
    parser.add_argument("--hash-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt-template", type=Path, default=DEFAULT_PROMPT_TEMPLATE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = build_request(
            consumer_root=args.consumer_root,
            program_root=args.program_root,
            template_copy=args.template_copy,
            rendered_prompt=args.rendered_prompt,
            hash_file=args.hash_file,
            output=args.output,
            prompt_template=args.prompt_template,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", **result["outputs"],
                      "template_sha256": result["template_sha256"],
                      "rendered_sha256": result["rendered_sha256"],
                      "timeout": TIMEOUT}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
