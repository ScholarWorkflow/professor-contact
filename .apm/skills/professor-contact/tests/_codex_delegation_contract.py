"""Producer-owned expected contract for Codex native delegation (issue #51).

The rows below are the deterministic tests' own expectation of which installed
custom agents delegate nested children under Codex and which are leaves.  They
are deliberately literal: tests read each agent document's target branch and
compare it against these rows mechanically — no NLP inference, no role-name
guessing.  When the producer's source contract changes on purpose, update the
rows in the same PR; never add a child to make a failing test pass.

Caller-level stage edges are intentionally kept out of the nested mapping:
`professor-contact-style-validator` after Stage 3 is delegated by the caller
thread as a sibling, not spawned by `professor-contact-idea-generator`.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".apm" / "agents"
SKILL_PATH = REPO_ROOT / ".apm" / "skills" / "professor-contact" / "SKILL.md"

# The 8 source agents; install projections (Codex TOML / OpenCode md) are
# keyed by these exact names.
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

# Agents whose Codex branch must delegate nested children via Codex's
# documented native custom-agent semantics (exact installed `name`, wait,
# no-inline, machine-failure blocker).  Children are exact installed custom
# agent names (repo-owned or upstream like professor-collector/paper-analysis).
CODEX_NESTED_DELEGATORS = {
    "professor-contact-downloader": ("professor-collector",),
    "professor-contact-analyzer": (
        "paper-analysis",
        "professor-contact-style-validator",
    ),
    "professor-contact-email-generator": (
        "professor-contact-email-validator",
    ),
}

# Agents that must not gain a nested delegation contract on Codex.
CODEX_NON_DELEGATORS = (
    "professor-contact",
    "professor-contact-idea-generator",
    "professor-contact-selection",
    "professor-contact-email-validator",
    "professor-contact-style-validator",
)

# Caller-level edges owned by SKILL.md's shared call table (Stage -> exact
# agent name), identical on both targets.
CODEX_CALLER_STAGE_EDGES = (
    (0, "professor-contact"),
    (1, "professor-contact-downloader"),
    (2, "professor-contact-analyzer"),
    (3, "professor-contact-idea-generator"),
    (4, "professor-contact-selection"),
    (5, "professor-contact-email-generator"),
)

# Caller-thread sibling edge: after the Stage 3 agent finalizes, the caller
# thread (never the idea-generator itself, on Codex) delegates the validator.
CODEX_CALLER_SIBLING_EDGES = (
    ("professor-contact-idea-generator", "professor-contact-style-validator"),
)

# Target-branch markers per agent document: (section start, section end).
# The end marker may be None, meaning "until the next same-level heading".
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

# SKILL.md caller-level Codex region (starts at the caller branch heading,
# runs through the Stage 3/4 and user-input boundary sections).
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
