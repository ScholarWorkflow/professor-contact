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
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
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


def agent_path(name: str) -> Path:
    return AGENTS_DIR / f"{name}.agent.md"


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
