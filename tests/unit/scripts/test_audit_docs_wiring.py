"""Tests for scripts/audit_docs_wiring.py (v1 skeleton + anchor check).

Covers Tasks 1+2 of docs/specs/docs-wiring-audit/tasks.md:

- Finding dataclass is frozen.
- Allowlist loader + reason-comment enforcement + glob matching.
- Slugify alignment with Python-Markdown's toc extension.
- Anchor extraction from markdown.
- Anchor integrity check (valid, broken, intra-page, external,
  cross-repo, target file missing).
- Markdown + JSON formatters.
- CLI: --help, --check, --format, exit codes.

Loads the script via importlib (matches the existing pattern in
tests/unit/help/test_coverage_script.py).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "audit_docs_wiring.py"


@pytest.fixture(scope="module")
def audit_module():
    """Load scripts/audit_docs_wiring.py as a module for testing."""
    spec = importlib.util.spec_from_file_location("_audit_docs_wiring", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_audit_docs_wiring"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------


class TestFinding:
    def test_finding_is_frozen(self, audit_module):
        """Finding must be immutable so callers can put it in sets."""
        f = audit_module.Finding(
            check="anchor",
            severity="error",
            file="docs/x.md",
            line=42,
            message="msg",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            f.line = 99  # type: ignore[misc]

    def test_finding_hashable(self, audit_module):
        """Frozen + no mutable defaults → hashable."""
        f = audit_module.Finding(
            check="anchor",
            severity="error",
            file="docs/x.md",
            line=42,
            message="msg",
        )
        assert {f}  # works in a set

    def test_finding_fix_optional(self, audit_module):
        f = audit_module.Finding(
            check="anchor",
            severity="error",
            file="docs/x.md",
            line=1,
            message="msg",
        )
        assert f.fix is None


# ---------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------


class TestSlugify:
    @pytest.mark.parametrize(
        "heading,expected",
        [
            ("My Section", "my-section"),
            ("My Section ✨", "my-section"),
            ("ChainExecutor", "chainexecutor"),
            ("Models & Execution", "models-execution"),
            ("agent-state / dynamic teams", "agent-state-dynamic-teams"),
            ("  leading and trailing  ", "leading-and-trailing"),
            ("UPPER_CASE", "upper_case"),
            ("", ""),
        ],
    )
    def test_slugify_matches_python_markdown(self, audit_module, heading, expected):
        """Slugify must mirror markdown.extensions.toc.slugify so anchor
        links resolve the same way mkdocs would at build time."""
        assert audit_module.slugify(heading) == expected


# ---------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------


class TestAllowlist:
    def test_empty_allowlist_returns_no_entries(self, audit_module, tmp_path):
        empty = tmp_path / "orphans.yml"
        empty.write_text("orphan_subtrees:\n", encoding="utf-8")
        al = audit_module.load_allowlist(empty)
        assert al.orphan_subtrees == ()

    def test_missing_file_returns_empty_allowlist(self, audit_module, tmp_path):
        missing = tmp_path / "nope.yml"
        al = audit_module.load_allowlist(missing)
        assert al.orphan_subtrees == ()

    def test_well_formed_allowlist_loads(self, audit_module, tmp_path):
        path = tmp_path / "orphans.yml"
        path.write_text(
            "orphan_subtrees:\n"
            "  # reason: blog posts are dated\n"
            "  - docs/blog/\n"
            "  # reason: archived material\n"
            "  - docs/archive/\n",
            encoding="utf-8",
        )
        al = audit_module.load_allowlist(path)
        assert al.orphan_subtrees == ("docs/blog/", "docs/archive/")

    def test_missing_reason_comment_raises(self, audit_module, tmp_path):
        path = tmp_path / "orphans.yml"
        path.write_text(
            "orphan_subtrees:\n  - docs/no-reason/\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="lacks a '# reason:' comment"):
            audit_module.load_allowlist(path)

    def test_wrong_comment_word_raises(self, audit_module, tmp_path):
        """A '#' comment without 'reason:' doesn't count."""
        path = tmp_path / "orphans.yml"
        path.write_text(
            "orphan_subtrees:\n  # this is a note, not a reason\n  - docs/foo/\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="lacks a '# reason:' comment"):
            audit_module.load_allowlist(path)

    def test_is_orphan_exempt_subtree(self, audit_module):
        al = audit_module.Allowlist(orphan_subtrees=("docs/blog/",))
        assert al.is_orphan_exempt("docs/blog/2026/post.md") is True
        assert al.is_orphan_exempt("docs/reference/x.md") is False

    def test_is_orphan_exempt_glob(self, audit_module):
        al = audit_module.Allowlist(orphan_subtrees=("docs/BLOG_*.md",))
        assert al.is_orphan_exempt("docs/BLOG_FOO.md") is True
        assert al.is_orphan_exempt("docs/blog/x.md") is False

    def test_is_orphan_exempt_exact(self, audit_module):
        al = audit_module.Allowlist(orphan_subtrees=("docs/index.md",))
        assert al.is_orphan_exempt("docs/index.md") is True
        assert al.is_orphan_exempt("docs/index2.md") is False


# ---------------------------------------------------------------------
# Heading extraction
# ---------------------------------------------------------------------


class TestExtractHeadings:
    def test_extracts_all_levels(self, audit_module):
        text = "# H1\n\n## H2\n\n### H3\n\nbody\n"
        anchors = audit_module._extract_headings(text)
        assert anchors == {"h1", "h2", "h3"}

    def test_strips_trailing_hash_marks(self, audit_module):
        text = "## My Section ##\n"
        assert audit_module._extract_headings(text) == {"my-section"}

    def test_empty_doc_returns_empty_set(self, audit_module):
        assert audit_module._extract_headings("") == set()


# ---------------------------------------------------------------------
# Anchor check
# ---------------------------------------------------------------------


@pytest.fixture
def docs_tree(tmp_path):
    """Build a minimal docs/ tree fixture."""
    docs = tmp_path / "docs"
    docs.mkdir()
    return docs


class TestHtmlAnchors:
    """HTML <a name="..."></a> / <a id="..."></a> anchors should be
    recognized in addition to slugified headings — pattern used by
    legacy markdown docs with emoji-prefixed headings."""

    def test_html_name_anchor_recognized(self, audit_module):
        text = "# Doc\n\n" '## <a name="big-idea"></a>🧠 The Big Idea\n\n' "content\n"
        anchors = audit_module._extract_headings(text)
        # Both the slugified heading AND the explicit HTML anchor
        # should be present.
        assert "big-idea" in anchors

    def test_html_id_anchor_recognized(self, audit_module):
        text = '<a id="my-section"></a>\n\n## Other Heading\n'
        anchors = audit_module._extract_headings(text)
        assert "my-section" in anchors

    def test_html_anchor_link_resolves(self, audit_module, docs_tree):
        """End-to-end: a link to #big-idea should resolve when the
        target doc uses an HTML name anchor instead of a heading."""
        (docs_tree / "tutorial.md").write_text(
            "# Tutorial\n\n"
            "[Jump](#big-idea)\n\n"
            '## <a name="big-idea"></a>🧠 The Big Idea\n\n'
            "content\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []


class TestInlineCodeSkip:
    """Links inside backtick-delimited inline code or fenced code
    blocks must NOT be flagged — they're documentation of the syntax,
    not real links."""

    def test_inline_code_link_skipped(self, audit_module, docs_tree):
        (docs_tree / "spec.md").write_text(
            "# Spec\n\n"
            "Links matching the pattern `[text](#anchor)` are "
            "documentation examples.\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []

    def test_double_backtick_link_skipped(self, audit_module, docs_tree):
        """`` `[text](#anchor)` `` (double backticks) — also skipped
        when the inner content is treated as inline code."""
        (docs_tree / "spec.md").write_text(
            "# Spec\n\n" "The link form `[text](#anchor)` is shown as code.\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []

    def test_fenced_code_block_link_skipped(self, audit_module, docs_tree):
        (docs_tree / "spec.md").write_text(
            "# Spec\n\n"
            "Example:\n\n"
            "```markdown\n"
            "[text](#anchor-that-does-not-exist)\n"
            "```\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []

    def test_real_link_outside_code_still_flagged(self, audit_module, docs_tree):
        """The inline-code skip must NOT mask real broken links that
        also happen to live in a doc with code examples."""
        (docs_tree / "spec.md").write_text(
            "# Spec\n\n"
            "See [missing](#nope-not-here) for details.\n\n"
            "Pattern: `[text](#example)` is documentation.\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert len(findings) == 1
        assert "nope-not-here" in findings[0].message


class TestCheckAnchors:
    def test_valid_anchor_no_finding(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n## Setup\n\nSee [setup](#setup) below.\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []

    def test_broken_intra_page_anchor(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n## Setup\n\nSee [missing](#nonexistent).\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert len(findings) == 1
        assert findings[0].check == "anchor"
        assert findings[0].severity == "error"
        assert "nonexistent" in findings[0].message
        assert findings[0].line is not None and findings[0].line >= 1

    def test_broken_cross_doc_anchor(self, audit_module, docs_tree):
        (docs_tree / "a.md").write_text(
            "# A\n\n[link to B](b.md#missing-section)\n",
            encoding="utf-8",
        )
        (docs_tree / "b.md").write_text(
            "# B\n\n## Real Section\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert len(findings) == 1
        assert "missing-section" in findings[0].message

    def test_valid_cross_doc_anchor(self, audit_module, docs_tree):
        (docs_tree / "a.md").write_text(
            "# A\n\n[link to B](b.md#real-section)\n",
            encoding="utf-8",
        )
        (docs_tree / "b.md").write_text(
            "# B\n\n## Real Section\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert findings == []

    def test_skips_external_https_link(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[external](https://example.com#anchor)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_skips_external_http_link(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[external](http://example.com#anchor)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_skips_mailto_link(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[email](mailto:a@b.com)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_skips_link_without_anchor(self, audit_module, docs_tree):
        """Links without `#` are file-existence checks (v1.1's nav check)."""
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[just file](other.md)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_skips_link_to_missing_file(self, audit_module, docs_tree):
        """Anchor check defers to nav-vs-fs for missing files."""
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[link](nope.md#anchor)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_skips_link_outside_docs(self, audit_module, docs_tree):
        """Links pointing outside docs/ (../src/...) are skipped."""
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n[outside](../src/foo.py#L42)\n",
            encoding="utf-8",
        )
        assert audit_module.check_anchors(docs_tree) == []

    def test_did_you_mean_hint_lists_real_anchors(self, audit_module, docs_tree):
        (docs_tree / "guide.md").write_text(
            "# Guide\n\n## One\n## Two\n## Three\n\n[bad](#nope)\n",
            encoding="utf-8",
        )
        findings = audit_module.check_anchors(docs_tree)
        assert len(findings) == 1
        # Hint should mention the available anchors.
        assert "one" in findings[0].message
        assert "two" in findings[0].message


# ---------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------


class TestFormatters:
    def test_format_markdown_empty(self, audit_module):
        assert audit_module.format_markdown([]) == "No findings."

    def test_format_markdown_groups_by_check(self, audit_module):
        findings = [
            audit_module.Finding(
                check="anchor",
                severity="error",
                file="docs/a.md",
                line=1,
                message="m1",
            ),
            audit_module.Finding(
                check="anchor",
                severity="error",
                file="docs/b.md",
                line=2,
                message="m2",
            ),
        ]
        out = audit_module.format_markdown(findings)
        assert "## anchor (2)" in out
        assert "docs/a.md" in out
        assert "docs/b.md" in out

    def test_format_markdown_escapes_pipes(self, audit_module):
        f = audit_module.Finding(
            check="anchor",
            severity="error",
            file="docs/a.md",
            line=1,
            message="has | pipe in it",
        )
        out = audit_module.format_markdown([f])
        # Pipe must be escaped inside the table cell so it doesn't
        # break the markdown table structure.
        assert "has \\| pipe" in out

    def test_format_json_empty(self, audit_module):
        out = audit_module.format_json([])
        assert json.loads(out) == {"findings": []}

    def test_format_json_round_trip(self, audit_module):
        f = audit_module.Finding(
            check="anchor",
            severity="error",
            file="docs/a.md",
            line=42,
            message="msg",
            fix="fix me",
        )
        out = audit_module.format_json([f])
        data = json.loads(out)
        assert data["findings"][0]["check"] == "anchor"
        assert data["findings"][0]["line"] == 42
        assert data["findings"][0]["fix"] == "fix me"


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------


class TestCLI:
    def test_help_lists_check_choices(self, audit_module, capsys):
        with pytest.raises(SystemExit) as exc_info:
            audit_module._parse_args(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--check" in captured.out
        assert "anchor" in captured.out

    def test_run_no_findings_exits_zero(self, audit_module, docs_tree, tmp_path):
        """Clean docs tree → exit 0, 'No findings.' markdown."""
        (docs_tree / "guide.md").write_text("# Guide\n\nNo links.\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = audit_module.run(
                [
                    "--check",
                    "anchor",
                    "--docs-root",
                    str(docs_tree),
                    "--allowlist",
                    str(tmp_path / "nope.yml"),
                ]
            )
        assert code == 0
        assert "No findings." in buf.getvalue()

    def test_run_findings_exits_one(self, audit_module, docs_tree, tmp_path):
        """Broken-anchor doc → exit 1."""
        (docs_tree / "guide.md").write_text("# Guide\n\n[bad](#missing)\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = audit_module.run(
                [
                    "--check",
                    "anchor",
                    "--docs-root",
                    str(docs_tree),
                    "--allowlist",
                    str(tmp_path / "nope.yml"),
                ]
            )
        assert code == 1

    def test_run_json_format_outputs_valid_json(self, audit_module, docs_tree, tmp_path):
        (docs_tree / "guide.md").write_text("# Guide\n\nNo links.\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            audit_module.run(
                [
                    "--check",
                    "anchor",
                    "--format",
                    "json",
                    "--docs-root",
                    str(docs_tree),
                    "--allowlist",
                    str(tmp_path / "nope.yml"),
                ]
            )
        data = json.loads(buf.getvalue())
        assert data == {"findings": []}

    def test_run_bad_allowlist_exits_two(self, audit_module, docs_tree, tmp_path):
        """Allowlist with missing reason comment → exit 2."""
        bad_allowlist = tmp_path / "orphans.yml"
        bad_allowlist.write_text("orphan_subtrees:\n  - docs/no-reason/\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = audit_module.run(
                [
                    "--docs-root",
                    str(docs_tree),
                    "--allowlist",
                    str(bad_allowlist),
                ]
            )
        assert code == 2


# ---------------------------------------------------------------------
# Nav ↔ filesystem check (Task 3)
# ---------------------------------------------------------------------


@pytest.fixture()
def repo_tree(tmp_path):
    """Repo-shaped fixture: docs/ + mkdocs.yml at the parent level."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (tmp_path / "mkdocs.yml").write_text(
        "site_name: t\nnav:\n  - Home: index.md\n", encoding="utf-8"
    )
    return docs


class TestCheckNav:
    def _write_mkdocs(self, docs, nav_yaml="nav:\n  - Home: index.md\n", extra=""):
        (docs.parent / "mkdocs.yml").write_text(
            f"site_name: t\n{nav_yaml}{extra}", encoding="utf-8"
        )

    def test_well_formed_nav_no_findings(self, audit_module, repo_tree):
        assert audit_module.check_nav(repo_tree) == []

    def test_dangling_nav_entry_is_error(self, audit_module, repo_tree):
        self._write_mkdocs(repo_tree, "nav:\n  - Home: index.md\n  - Gone: missing.md\n")
        findings = audit_module.check_nav(repo_tree)
        assert [f.severity for f in findings] == ["error"]
        assert "missing.md" in findings[0].message

    def test_orphan_doc_not_allowlisted_is_error(self, audit_module, repo_tree):
        (repo_tree / "stray.md").write_text("# Stray\n", encoding="utf-8")
        findings = audit_module.check_nav(repo_tree)
        assert len(findings) == 1
        assert findings[0].severity == "error"
        assert "orphan" in findings[0].message

    def test_orphan_doc_allowlisted_is_exempt(self, audit_module, repo_tree):
        (repo_tree / "stray.md").write_text("# Stray\n", encoding="utf-8")
        allow = audit_module.Allowlist(orphan_subtrees=("docs/stray.md",))
        assert audit_module.check_nav(repo_tree, allow) == []

    def test_nested_nav_structure(self, audit_module, repo_tree):
        (repo_tree / "guide").mkdir()
        (repo_tree / "guide" / "a.md").write_text("# A\n", encoding="utf-8")
        self._write_mkdocs(
            repo_tree,
            "nav:\n  - Home: index.md\n  - Guide:\n      - Part A:\n          - guide/a.md\n",
        )
        assert audit_module.check_nav(repo_tree) == []

    def test_excluded_doc_is_not_orphan(self, audit_module, repo_tree):
        (repo_tree / "internal").mkdir()
        (repo_tree / "internal" / "x.md").write_text("# X\n", encoding="utf-8")
        self._write_mkdocs(
            repo_tree,
            "nav:\n  - Home: index.md\n",
            "exclude_docs: |\n  internal/\n",
        )
        assert audit_module.check_nav(repo_tree) == []

    def test_hook_injected_features_root_is_exempt(self, audit_module, repo_tree):
        (repo_tree / "features").mkdir()
        (repo_tree / "features" / "hub.md").write_text("# Hub\n", encoding="utf-8")
        assert audit_module.check_nav(repo_tree) == []

    def test_projector_feature_page_is_exempt(self, audit_module, repo_tree):
        help_dir = repo_tree.parent / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text(
            "features:\n  spec-engine:\n    description: d\n", encoding="utf-8"
        )
        (repo_tree / "reference").mkdir()
        (repo_tree / "reference" / "spec-engine.md").write_text("# S\n", encoding="utf-8")
        (repo_tree / "reference" / "not-a-feature.md").write_text("# N\n", encoding="utf-8")
        findings = audit_module.check_nav(repo_tree)
        flagged = {f.file for f in findings}
        assert "docs/reference/not-a-feature.md" in flagged
        assert "docs/reference/spec-engine.md" not in flagged

    def test_missing_mkdocs_yml_is_warning_not_error(self, audit_module, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        findings = audit_module.check_nav(docs)
        assert [f.severity for f in findings] == ["warning"]


# ---------------------------------------------------------------------
# features.yaml check (Task 4, adapted)
# ---------------------------------------------------------------------


class TestCheckFeaturesYaml:
    def _write_features(self, docs, body):
        help_dir = docs.parent / ".help"
        help_dir.mkdir(exist_ok=True)
        (help_dir / "features.yaml").write_text(body, encoding="utf-8")

    def test_valid_docs_entries_no_findings(self, audit_module, repo_tree):
        self._write_features(repo_tree, "_docs:\n  - docs/index.md\n")
        assert audit_module.check_features_yaml(repo_tree) == []

    def test_dangling_docs_entry_is_error(self, audit_module, repo_tree):
        self._write_features(repo_tree, "_docs:\n  - docs/index.md\n  - docs/gone.md\n")
        findings = audit_module.check_features_yaml(repo_tree)
        assert [f.severity for f in findings] == ["error"]
        assert "docs/gone.md" in findings[0].message

    def test_missing_features_yaml_no_findings(self, audit_module, repo_tree):
        assert audit_module.check_features_yaml(repo_tree) == []

    def test_unparseable_features_yaml_is_warning(self, audit_module, repo_tree):
        self._write_features(repo_tree, "_docs: [unclosed\n")
        findings = audit_module.check_features_yaml(repo_tree)
        assert [f.severity for f in findings] == ["warning"]


# ---------------------------------------------------------------------
# mkdocstrings symbol resolution (Task 9)
# ---------------------------------------------------------------------


class TestCheckMkdocstrings:
    def test_valid_stdlib_symbol_resolves(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text("# API\n\n::: json.dumps\n", encoding="utf-8")
        assert audit_module.check_mkdocstrings(repo_tree) == []

    def test_missing_module_is_error(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text("::: no_such_module_xyz.Thing\n", encoding="utf-8")
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert [f.severity for f in findings] == ["error"]
        assert "no_such_module_xyz.Thing" in findings[0].message

    def test_missing_attribute_is_error(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text("::: json.no_such_attr\n", encoding="utf-8")
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert [f.severity for f in findings] == ["error"]

    def test_malformed_directive_not_matched(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text("::: not a dotted path!\n:::\n", encoding="utf-8")
        assert audit_module.check_mkdocstrings(repo_tree) == []

    def test_reports_file_and_line(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text("# API\n\n::: no_such_module_xyz\n", encoding="utf-8")
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert findings[0].file == "docs/api.md"
        assert findings[0].line == 3


# ---------------------------------------------------------------------
# Exit-code severity gating (v1.1)
# ---------------------------------------------------------------------


class TestWarningsAreAdvisory:
    def test_warning_only_findings_exit_zero(self, audit_module, tmp_path):
        """A repo with no mkdocs.yml yields a nav warning — exit stays 0."""
        docs = tmp_path / "docs"
        docs.mkdir()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = audit_module.run(
                ["--check", "nav", "--docs-root", str(docs), "--allowlist", str(tmp_path / "n.yml")]
            )
        assert code == 0


class TestMkdocstringsBatchResilience:
    def test_batch_resolves_mixed_ok_and_fail(self, audit_module, repo_tree):
        (repo_tree / "api.md").write_text(
            "::: json.dumps\n\ntext\n\n::: no_such_module_xyz.Thing\n", encoding="utf-8"
        )
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert len(findings) == 1
        assert "no_such_module_xyz.Thing" in findings[0].message

    def test_timeout_surfaces_as_findings_not_crash(self, audit_module, repo_tree, monkeypatch):
        """A hanging import must yield per-directive findings, not an exception."""
        import subprocess

        def _fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="python", timeout=120)

        monkeypatch.setattr(subprocess, "run", _fake_run)
        (repo_tree / "api.md").write_text("::: json.dumps\n", encoding="utf-8")
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert [f.severity for f in findings] == ["error"]
        assert "timed out" in findings[0].message

    def test_duplicate_directives_resolved_once_flagged_everywhere(self, audit_module, repo_tree):
        (repo_tree / "a.md").write_text("::: no_such_module_xyz\n", encoding="utf-8")
        (repo_tree / "b.md").write_text("::: no_such_module_xyz\n", encoding="utf-8")
        findings = audit_module.check_mkdocstrings(repo_tree)
        assert {f.file for f in findings} == {"docs/a.md", "docs/b.md"}
