"""Drift guard for the always-loaded rules budget (rules-corpus-jit).

Claude Code eagerly loads every ``.md`` under ``.claude/rules/``
EXCEPT files whose YAML frontmatter declares ``paths:`` (those load
only when a matching file is read). This suite pins the eager set to
an explicit allowlist and a byte budget so new rules must either
path-scope, live in ``.claude/rules-tail/`` behind the INDEX, or
consciously widen the allowlist in the same diff.

See docs/specs/rules-corpus-jit/ (D4).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = REPO_ROOT / ".claude" / "rules"
TAIL_DIR = REPO_ROOT / ".claude" / "rules-tail"
INDEX = RULES_DIR / "attune" / "INDEX.md"

# Files allowed to load eagerly (no ``paths:`` frontmatter).
RESIDENT_ALLOWLIST = {
    "INDEX.md",
    "decision-routine.md",
    "xml-enhanced-prompts.md",
    "output-formatting.md",
}

# Hard ceiling for the eager set, in bytes (was 116,590 pre-cutover).
EAGER_BUDGET_BYTES = 20_000


def _has_paths_frontmatter(path: Path) -> bool:
    """True if the file opens with YAML frontmatter declaring paths:."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    frontmatter = text[4:end]
    return any(
        line.rstrip() == "paths:" or line.startswith("paths:") for line in frontmatter.splitlines()
    )


def _eager_rules() -> list[Path]:
    return [p for p in sorted(RULES_DIR.rglob("*.md")) if not _has_paths_frontmatter(p)]


def test_eager_rules_are_allowlisted() -> None:
    """Every unconditionally-loaded rules file is a deliberate choice."""
    unexpected = [
        str(p.relative_to(REPO_ROOT)) for p in _eager_rules() if p.name not in RESIDENT_ALLOWLIST
    ]
    assert not unexpected, (
        "New always-loaded rules file(s) — add paths: frontmatter, move "
        "to .claude/rules-tail/, or widen RESIDENT_ALLOWLIST "
        f"deliberately: {unexpected}"
    )


def test_eager_rules_within_budget() -> None:
    """The eager set stays under the residency byte budget."""
    total = sum(p.stat().st_size for p in _eager_rules())
    assert total <= EAGER_BUDGET_BYTES, (
        f"Always-loaded rules total {total} bytes > "
        f"{EAGER_BUDGET_BYTES} budget — demote something (see "
        "docs/specs/rules-corpus-jit/)"
    )


def test_index_covers_every_demoted_rule() -> None:
    """INDEX.md names every tail rule and every path-scoped rule."""
    index_text = INDEX.read_text(encoding="utf-8")
    missing = []
    for p in sorted(TAIL_DIR.rglob("*.md")):
        if p.name not in index_text:
            missing.append(f"tail:{p.name}")
    for p in sorted(RULES_DIR.rglob("*.md")):
        if _has_paths_frontmatter(p) and p.name not in index_text:
            missing.append(f"scoped:{p.name}")
    assert not missing, f"INDEX.md is missing trigger lines for: {missing}"


def test_scoped_globs_match_real_paths() -> None:
    """Every paths: glob in a scoped rule matches something that exists
    (or names an explicit file) — a typo'd glob would silently never
    load the rule."""
    import re

    for p in sorted(RULES_DIR.rglob("*.md")):
        if not _has_paths_frontmatter(p):
            continue
        text = p.read_text(encoding="utf-8")
        end = text.find("\n---", 4)
        globs = re.findall(r'-\s+"([^"]+)"', text[4:end])
        assert globs, f"{p.name}: paths: frontmatter with no globs"
        for g in globs:
            matched = next(iter(REPO_ROOT.glob(g)), None)
            assert matched is not None, f"{p.name}: glob {g!r} matches nothing"
