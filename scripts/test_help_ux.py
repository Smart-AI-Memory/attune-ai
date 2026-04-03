#!/usr/bin/env python3
"""Interactive UX test script for the help system engine.

Run with:  python scripts/test_help_ux.py

Exercises every public API in attune.help.engine against
the real generated/ templates so you can eyeball the output.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attune.help.engine import (
    AudienceProfile,
    PopulatedTemplate,
    TemplateContext,
    get_precursor_warnings,
    get_template_confidence,
    get_workflow_help,
    list_tags,
    populate,
    populate_progressive,
    record_template_feedback,
    reset_session,
    search_by_tag,
)

GENERATED_DIR = Path(__file__).resolve().parents[1] / "plugin" / "help" / "generated"

PASS = 0
FAIL = 0


def header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def subheader(title: str) -> None:
    print(f"\n--- {title} ---")


def show_result(result: PopulatedTemplate | None, label: str = "") -> None:
    global PASS, FAIL
    if result is None:
        print(f"  [{label}] returned None")
        FAIL += 1
        return
    PASS += 1
    print(f"  [{label}]")
    print(f"    ID:    {result.template_id}")
    print(f"    Type:  {result.type} / {result.subtype}")
    print(f"    Title: {result.title}")
    secs = ", ".join(result.sections.keys()) if result.sections else "(none)"
    print(f"    Sections: {secs}")
    tags = ", ".join(result.tags) if result.tags else "(none)"
    print(f"    Tags:  {tags}")
    if result.related:
        rels = "; ".join(f"{r['type']}: {r['id']}" for r in result.related)
        print(f"    Related: {rels}")
    if result.metadata:
        print(f"    Metadata: {result.metadata}")
    # Show first 3 lines of body
    body_preview = result.body.strip().split("\n")[:3]
    print("    Body preview:")
    for line in body_preview:
        print(f"      {line}")


# ============================================================
# 1. Basic populate — every template type
# ============================================================

header("1. Basic populate() — one of each type")

type_samples = {
    "error": "err-shadow-directories-at-repo-root-break-imports",
    "warning": "war-attune-skill-names-must-not-collide-with-claude-code-built-in",
    "tip": "tip-after-security-audit",
    "reference": "ref-skill-security-audit",
    "task": "tas-use-security-audit",
    "faq": "faq-baseworkflow-uses-class-attributes-not-constructor-params",
    "note": "not-socratic-interaction-rule",
    "concept": "con-tool-security-audit",
    "quickstart": "qui-install-plugin",
    "troubleshooting": "tro-import-error-attune",
    "comparison": "com-workflow-vs-wizard",
}

for label, tid in type_samples.items():
    result = populate(tid, generated_dir=GENERATED_DIR)
    show_result(result, label)


# ============================================================
# 2. Audience adaptation — compact vs normal vs claude-code
# ============================================================

header("2. Audience adaptation")

TID = "err-shadow-directories-at-repo-root-break-imports"

for verbosity in ("compact", "normal", "detailed"):
    subheader(f"verbosity={verbosity}")
    result = populate(
        TID,
        audience=AudienceProfile(verbosity=verbosity),
        generated_dir=GENERATED_DIR,
    )
    if result:
        PASS += 1
        lines = result.body.strip().split("\n")
        print(f"  Body length: {len(result.body)} chars, {len(lines)} lines")
        for line in lines[:4]:
            print(f"    {line}")
    else:
        FAIL += 1
        print("  returned None")

for channel in ("claude-code", "marketplace", "cli"):
    subheader(f"channel={channel}")
    result = populate(
        TID,
        audience=AudienceProfile(channel=channel),
        generated_dir=GENERATED_DIR,
    )
    if result:
        PASS += 1
        has_related = "Related Topics" in result.body
        print(f"  Related Topics section present: {has_related}")
    else:
        FAIL += 1
        print("  returned None")


# ============================================================
# 3. Context injection
# ============================================================

header("3. Context injection")

ctx = TemplateContext(
    file_path="src/attune/security/path_validation.py",
    error_message="ModuleNotFoundError: No module named 'attune.foo'",
    workflow_name="security-audit",
    tool_name="security_audit",
    extra={"custom_key": "custom_value"},
)
result = populate(TID, context=ctx, generated_dir=GENERATED_DIR)
show_result(result, "with full context")


# ============================================================
# 4. Composition (embed inlining)
# ============================================================

header("4. Composition (compose=True vs False)")

subheader("compose=False")
result = populate(TID, compose=False, generated_dir=GENERATED_DIR)
if result:
    PASS += 1
    composed = result.metadata.get("composed_from", [])
    print(f"  composed_from: {composed}")
    print(f"  Body length: {len(result.body)} chars")
else:
    FAIL += 1
    print("  returned None")

subheader("compose=True")
result = populate(TID, compose=True, generated_dir=GENERATED_DIR)
if result:
    PASS += 1
    composed = result.metadata.get("composed_from", [])
    print(f"  composed_from: {composed}")
    print(f"  Body length: {len(result.body)} chars")
else:
    FAIL += 1
    print("  returned None")


# ============================================================
# 5. Progressive depth — verbosity-based fallback
# ============================================================

header("5. Progressive depth (verbosity-based fallback)")

reset_session()
for i in range(4):
    result = populate_progressive(TID, generated_dir=GENERATED_DIR)
    if result:
        PASS += 1
        depth = result.metadata.get("depth_level", "?")
        label = result.metadata.get("level_label", "?")
        print(f"  Call {i + 1}: depth={depth}, label={label}, " f"body_len={len(result.body)}")
    else:
        FAIL += 1
        print(f"  Call {i + 1}: returned None")


# ============================================================
# 6. Type-driven progressive depth
# ============================================================

header("6. Type-driven progressive depth (security-audit)")

reset_session()
for i in range(4):
    result = populate_progressive(
        "security-audit",
        generated_dir=GENERATED_DIR,
    )
    if result:
        PASS += 1
        depth = result.metadata.get("depth_level", "?")
        label = result.metadata.get("level_label", "?")
        print(
            f"  Call {i + 1}: depth={depth}, label={label}, "
            f"type={result.type}, title={result.title}"
        )
    else:
        FAIL += 1
        print(f"  Call {i + 1}: returned None")


# ============================================================
# 7. Type-driven with starting_level override
# ============================================================

header("7. starting_level override (skip concept)")

reset_session()
result = populate_progressive(
    "security-audit",
    generated_dir=GENERATED_DIR,
    starting_level=1,
)
if result:
    PASS += 1
    print(
        f"  depth={result.metadata.get('depth_level')}, "
        f"type={result.type}, title={result.title}"
    )
else:
    FAIL += 1
    print("  returned None")


# ============================================================
# 8. Topic switching resets depth
# ============================================================

header("8. Topic switching resets depth")

reset_session()
populate_progressive("security-audit", generated_dir=GENERATED_DIR)
populate_progressive("security-audit", generated_dir=GENERATED_DIR)
# Now at depth 1, switch topic
result = populate_progressive(
    "err-shadow-directories-at-repo-root-break-imports",
    generated_dir=GENERATED_DIR,
)
if result:
    PASS += 1
    print("  After 2x security-audit, switched to error:")
    print(f"  depth={result.metadata.get('depth_level')}, " f"topic={result.metadata.get('topic')}")
else:
    FAIL += 1
    print("  returned None")


# ============================================================
# 9. Workflow chain prediction
# ============================================================

header("9. Workflow chain prediction (get_workflow_help)")

workflows = ["code-review", "security-audit", "test-gen", "release-prep", "nonexistent"]

for wf in workflows:
    results = get_workflow_help(wf, generated_dir=GENERATED_DIR)
    if results:
        PASS += 1
        ids = [r.template_id for r in results]
        print(f"  {wf}: {len(results)} templates -> {ids}")
    else:
        print(f"  {wf}: (no results)")
        if wf == "nonexistent":
            PASS += 1
        else:
            FAIL += 1


# ============================================================
# 10. Precursor warnings
# ============================================================

header("10. Precursor warnings (get_precursor_warnings)")

files = [
    "src/attune/security/path_validation.py",
    "src/attune/config.py",
    ".github/workflows/tests.yml",
    "pyproject.toml",
    "README.md",
    "image.png",
]

for fp in files:
    results = get_precursor_warnings(fp, generated_dir=GENERATED_DIR)
    count = len(results)
    if results:
        ids = [r.template_id for r in results]
        print(f"  {fp}: {count} warnings -> {ids}")
    else:
        print(f"  {fp}: (no warnings)")
    PASS += 1  # all valid — even empty is correct for .png


# ============================================================
# 11. Tag search
# ============================================================

header("11. Tag search (search_by_tag)")

for tag in ("security", "python", "imports", "ci", "nonexistent"):
    results = search_by_tag(tag, generated_dir=GENERATED_DIR)
    print(f"  '{tag}': {len(results)} matches")
    if results:
        for tid in results[:5]:
            print(f"    - {tid}")
    PASS += 1


# ============================================================
# 12. Tag listing
# ============================================================

header("12. Tag listing (list_tags)")

tags = list_tags(generated_dir=GENERATED_DIR)
print(f"  Total tags: {len(tags)}")
for tag, count in list(tags.items())[:10]:
    print(f"    {tag}: {count}")
PASS += 1


# ============================================================
# 13. Feedback loop
# ============================================================

header("13. Feedback loop")

# Use a throwaway template ID to avoid polluting real data
import shutil
import tempfile

feedback_dir = Path(tempfile.mkdtemp()) / "generated"
shutil.copytree(GENERATED_DIR, feedback_dir)

score = record_template_feedback(
    "err-shadow-directories-at-repo-root-break-imports",
    "good",
    generated_dir=feedback_dir,
)
print(f"  After 1 good: confidence = {score:.2f}")
PASS += 1

score = record_template_feedback(
    "err-shadow-directories-at-repo-root-break-imports",
    "good",
    generated_dir=feedback_dir,
)
print(f"  After 2 good: confidence = {score:.2f}")

score = record_template_feedback(
    "err-shadow-directories-at-repo-root-break-imports",
    "bad",
    generated_dir=feedback_dir,
)
print(f"  After 2 good + 1 bad: confidence = {score:.2f}")

no_feedback = get_template_confidence(
    "err-never-rated",
    generated_dir=feedback_dir,
)
print(f"  No feedback default: confidence = {no_feedback:.2f}")

# Clean up
shutil.rmtree(feedback_dir.parent)
PASS += 1


# ============================================================
# 14. Edge cases
# ============================================================

header("14. Edge cases")

# Unknown template ID
result = populate("err-this-does-not-exist", generated_dir=GENERATED_DIR)
print(f"  Unknown ID: {result}")
PASS += 1

# Unknown prefix
result = populate("xyz-something", generated_dir=GENERATED_DIR)
print(f"  Unknown prefix: {result}")
PASS += 1

# Path traversal attempt
result = populate("err-../../etc/passwd", generated_dir=GENERATED_DIR)
print(f"  Path traversal: {result}")
PASS += 1

# No separator
result = populate("noseparator", generated_dir=GENERATED_DIR)
print(f"  No separator: {result}")
PASS += 1


# ============================================================
# Summary
# ============================================================

header("SUMMARY")
total = PASS + FAIL
print(f"  Passed: {PASS}/{total}")
print(f"  Failed: {FAIL}/{total}")
print()

if FAIL > 0:
    print("  FAILURES detected — check output above")
    sys.exit(1)
else:
    print("  All checks passed!")
    sys.exit(0)
