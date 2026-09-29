import json
import re
import unittest
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[4]
DOWNLOADER = REPO_ROOT / ".apm" / "agents" / "professor-contact-downloader.agent.md"
TARGET_NAME = "套磁目标.json"
STAGE1_NAME = "套磁阶段1候选.json"


def _json_blocks(text: str) -> list[dict]:
    payloads = []
    for block in re.findall(r"```json\n(.*?)```", text, flags=re.DOTALL):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _path_parent(value: str, filename: str) -> str | None:
    path = PurePosixPath(value)
    if path.name != filename:
        return None
    return str(path.parent)


def _transaction_parent(record: dict) -> str | None:
    strings = list(_strings(record))
    target_parents = {
        parent for value in strings
        if (parent := _path_parent(value, TARGET_NAME)) is not None
    }
    stage1_parents = {
        parent for value in strings
        if (parent := _path_parent(value, STAGE1_NAME)) is not None
    }
    if len(target_parents) != 1 or target_parents != stage1_parents:
        return None
    parent = next(iter(target_parents))
    # The transaction itself must carry canonical professor_dir, not merely
    # make it reconstructible from a display-name-keyed pair of path maps.
    if parent not in strings:
        return None
    return parent


def _transaction_containers(value):
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        parents = [_transaction_parent(item) for item in value]
        if all(parent is not None for parent in parents):
            yield "list", value, parents
    elif isinstance(value, dict) and value:
        if all(isinstance(item, dict) for item in value.values()):
            parents = [_transaction_parent(item) for item in value.values()]
            if all(parent is not None for parent in parents):
                # A mapping form is collision-safe only when its machine key is
                # the canonical professor_dir itself. Display names are forbidden.
                if set(value.keys()) == set(parents):
                    yield "canonical_map", value, parents
        for item in value.values():
            yield from _transaction_containers(item)


def _has_display_keyed_state_path_map(value) -> bool:
    if isinstance(value, dict):
        if value and all(isinstance(item, str) for item in value.values()):
            state_paths = []
            for item in value.values():
                path = PurePosixPath(item)
                if path.name in {TARGET_NAME, STAGE1_NAME}:
                    state_paths.append((item, str(path.parent)))
            if state_paths:
                for key, (path_value, parent) in zip(value.keys(), state_paths):
                    if key not in {path_value, parent}:
                        return True
        return any(_has_display_keyed_state_path_map(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_display_keyed_state_path_map(item) for item in value)
    return False


class Stage1HandoffIdentityTests(unittest.TestCase):
    def test_issue65_stage1_transient_handoff_is_collision_free(self):
        """C65-03: the shipped Stage-1 result cannot collapse same-name professors."""
        payloads = [
            payload for payload in _json_blocks(DOWNLOADER.read_text(encoding="utf-8"))
            if "result" in payload and any(
                PurePosixPath(value).name == STAGE1_NAME for value in _strings(payload)
            )
        ]
        self.assertTrue(payloads, "no active Stage-1 result JSON block found")

        for payload in payloads:
            self.assertFalse(
                _has_display_keyed_state_path_map(payload),
                "Stage-1 result still exposes a state-path mapping keyed by display identity",
            )
            containers = list(_transaction_containers(payload))
            self.assertTrue(
                containers,
                "Stage-1 result has no collision-free professor-local transaction records",
            )
            for _kind, _container, parents in containers:
                self.assertEqual(
                    len(parents), len(set(parents)),
                    "two returned transactions share one canonical professor_dir",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
