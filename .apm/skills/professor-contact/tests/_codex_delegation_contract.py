"""Producer-owned source inventory for Codex delegation invariants (issue #51).

This helper deliberately does *not* encode expected child identities.  The
pinned fixtures@9 contract makes named-role identity an optional diagnostic:
requested_role / loaded_identity, including mismatch or unobservable states,
must never become a merge gate for a delegation-confirmed run.

The deterministic tests therefore identify only which repo-owned source
documents are coordinators versus leaves, then verify generic orchestration
invariants (native delegation, wait, no-inline, fail-closed, target isolation).
They do not assert which named child was requested or loaded.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ROOT_AGENTS = REPO_ROOT / ".apm" / "agents"
OPENCODE_AGENTS = REPO_ROOT / "packages" / "professor-contact-opencode" / ".apm" / "agents"
CODEX_AGENTS = REPO_ROOT / "packages" / "professor-contact-codex" / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"

ALL_AGENT_NAMES = (
    "professor-contact",
    "professor-contact-downloader",
    "professor-contact-analyzer",
    "professor-contact-idea-generator",
    "professor-contact-selection",
    "professor-contact-email-generator",
    "professor-contact-email-validator",
    "professor-contact-style-validator",
)

# Source documents that own nested orchestration.  This is a source-file
# inventory only; it intentionally carries no expected child name/identity.
CODEX_NESTED_DELEGATOR_AGENTS = (
    "professor-contact-downloader",
    "professor-contact-analyzer",
    "professor-contact-email-generator",
)

# Source documents that must not gain a nested delegation contract on Codex.
CODEX_NON_DELEGATORS = (
    "professor-contact",
    "professor-contact-idea-generator",
    "professor-contact-selection",
    "professor-contact-email-validator",
    "professor-contact-style-validator",
)

# Target-branch markers per coordinator source document.
CODEX_BRANCH_MARKERS = {
    "professor-contact-downloader": (
        "**Codex (non-interactive)**",
        "- This is the **item-scoped PDF fill fast path**",
    ),
    "professor-contact-analyzer": ("### Codex 分支", "## Input"),
    "professor-contact-email-generator": (
        "### Codex branch",
        "### humanizer-ja stage-5 constraints",
    ),
}

OPENCODE_BRANCH_MARKERS = {
    "professor-contact-downloader": (
        "**OpenCode (native Task/subagent delegation)**",
        "**Codex (non-interactive)**",
    ),
    "professor-contact-analyzer": ("### OpenCode 分支", "### Codex 分支"),
    "professor-contact-email-generator": (
        "### OpenCode branch",
        "### Codex branch",
    ),
}

SKILL_CODEX_REGION = ("### Codex 分支", "### Input contract")


# Agents that exist only as per-target projections (not in the shared root
# .apm/agents).  Every other agent document is target-agnostic and lives at the
# repository root.
TARGET_SCOPED_AGENTS = {"professor-contact-analyzer"}


def codex_agent_path(name: str) -> Path:
    if name in TARGET_SCOPED_AGENTS:
        return CODEX_AGENTS / f"{name}.agent.md"
    return ROOT_AGENTS / f"{name}.agent.md"


def opencode_agent_path(name: str) -> Path:
    if name in TARGET_SCOPED_AGENTS:
        return OPENCODE_AGENTS / f"{name}.agent.md"
    return ROOT_AGENTS / f"{name}.agent.md"


def all_production_source_paths() -> list[Path]:
    """Every repo-owned production source document the invariants read.

    The shared root agents plus the two target-scoped analyzer projections.
    The root analyzer deliberately does not exist after issue #47, so it is not
    listed here.
    """
    paths: list[Path] = [SKILL_PATH]
    for name in ALL_AGENT_NAMES:
        if name in TARGET_SCOPED_AGENTS:
            paths.append(codex_agent_path(name))
            paths.append(opencode_agent_path(name))
        else:
            paths.append(ROOT_AGENTS / f"{name}.agent.md")
    return paths


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter_and_body(path: Path):
    text = read(path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1 :])


def segment(text: str, start_marker: str, end_marker: str | None) -> str:
    start = text.index(start_marker)
    if end_marker is None:
        return text[start:]
    end = text.index(end_marker, start + len(start_marker))
    return text[start:end]
