#!/usr/bin/env python3
"""Run all documentation template generators.

Executes Error, Warning, Tip, and Reference generators in
sequence, then builds cross-links and source manifest.

Supports:
    --check     Verify all generated content is in sync
    --stale     Check if sources changed since last generation
    --coverage  Report undocumented features

Usage:
    python scripts/generate_all.py              # Generate all
    python scripts/generate_all.py --check      # Verify sync
    python scripts/generate_all.py --stale      # Check staleness
    python scripts/generate_all.py --coverage   # Check coverage
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_cross_links import main as build_cross_links
from generate_error_templates import main as generate_errors
from generate_reference_templates import main as generate_references
from generate_tip_templates import main as generate_tips
from generate_warning_templates import main as generate_warnings


def _repo_root() -> Path:
    """Get repository root path."""
    return Path(__file__).resolve().parent.parent


def _hash_file(path: Path) -> str:
    """SHA-256 hash of a file's contents.

    Args:
        path: File to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -----------------------------------------------------------
# Source manifest: tracks which source file produced each
# generated template, enabling staleness detection.
# -----------------------------------------------------------


def _build_source_manifest(generated_dir: Path) -> dict:
    """Build source manifest from generated templates.

    Reads each template's frontmatter 'source' field and
    hashes the corresponding source file.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Manifest dict ready for JSON serialization.
    """
    import frontmatter

    repo = _repo_root()
    manifest: dict[str, dict] = {}
    now = datetime.now(timezone.utc).isoformat()

    type_dirs = ["errors", "warnings", "tips", "references"]

    for type_dir_name in type_dirs:
        type_dir = generated_dir / type_dir_name
        if not type_dir.exists():
            continue

        prefix = {"errors": "err", "warnings": "war", "tips": "tip", "references": "ref"}[
            type_dir_name
        ]

        for md_file in sorted(type_dir.glob("*.md")):
            try:
                post = frontmatter.load(str(md_file))
            except Exception:  # noqa: BLE001
                # INTENTIONAL: skip unparseable files
                continue

            source_rel = post.get("source", "")
            if not source_rel:
                continue

            source_path = repo / source_rel
            if not source_path.exists():
                continue

            template_id = f"{prefix}-{md_file.stem}"
            manifest[template_id] = {
                "source": source_rel,
                "hash": _hash_file(source_path),
                "generated_at": now,
            }

    return dict(sorted(manifest.items()))


def _write_manifest(generated_dir: Path) -> int:
    """Generate source_manifest.json.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Number of entries written.
    """
    manifest = _build_source_manifest(generated_dir)
    output = generated_dir / "source_manifest.json"
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    output.write_text(rendered, encoding="utf-8")
    return len(manifest)


def check_staleness(generated_dir: Path) -> int:
    """Check if sources changed since last generation.

    Compares current source file hashes against stored
    manifest. Reports stale templates.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Exit code: 0 if none stale, 1 if any stale.
    """
    repo = _repo_root()
    manifest_path = generated_dir / "source_manifest.json"

    if not manifest_path.exists():
        print("No source_manifest.json found.")
        print("Run: python scripts/generate_all.py")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stale: list[str] = []

    for template_id, entry in manifest.items():
        source_path = repo / entry["source"]
        if not source_path.exists():
            stale.append(f"  {template_id}: source missing ({entry['source']})")
            continue

        current_hash = _hash_file(source_path)
        if current_hash != entry["hash"]:
            stale.append(f"  {template_id}: source changed ({entry['source']})")

    if stale:
        print(f"Stale templates ({len(stale)}):\n")
        for line in stale[:20]:
            print(line)
        if len(stale) > 20:
            print(f"  ... and {len(stale) - 20} more")
        print("\nRun: python scripts/generate_all.py")
        return 1

    print(f"All {len(manifest)} templates up to date.")
    return 0


# -----------------------------------------------------------
# Coverage analysis: find undocumented features.
# -----------------------------------------------------------


def check_coverage(generated_dir: Path) -> int:
    """Check for undocumented features.

    Scans skill directories and MCP tool schemas, reports
    items without corresponding reference templates.

    Args:
        generated_dir: Path to plugin/help/generated/.

    Returns:
        Exit code: 0 if full coverage, 1 if gaps.
    """
    repo = _repo_root()
    refs_dir = generated_dir / "references"
    existing_refs = {f.stem for f in refs_dir.glob("*.md")} if refs_dir.exists() else set()

    gaps: list[str] = []

    # Check skills
    skills_dir = repo / "plugin" / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not (skill_dir / "SKILL.md").exists():
                continue
            expected = f"skill-{skill_dir.name}"
            if expected not in existing_refs:
                gaps.append(f"  MISSING: skill '{skill_dir.name}' has no reference template")

    # Check MCP tools
    tool_schemas_path = repo / "src" / "attune" / "mcp" / "tool_schemas.py"
    if tool_schemas_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("tool_schemas", tool_schemas_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for group_fn_name in ["get_workflow_tools", "get_utility_tools", "get_memory_tools"]:
                get_fn = getattr(module, group_fn_name, None)
                if not get_fn:
                    continue
                for tool_name in get_fn():
                    expected = f"tool-{tool_name.replace('_', '-')}"
                    if expected not in existing_refs:
                        gaps.append(f"  MISSING: tool '{tool_name}' has no reference template")

    if gaps:
        print(f"Coverage gaps ({len(gaps)}):\n")
        for line in gaps:
            print(line)
        return 1

    skill_count = sum(1 for r in existing_refs if r.startswith("skill-"))
    tool_count = sum(1 for r in existing_refs if r.startswith("tool-"))
    print(f"Full coverage: {skill_count} skills, {tool_count} tools documented.")
    return 0


# -----------------------------------------------------------
# Main: orchestrate all generators + new flags.
# -----------------------------------------------------------


def main() -> int:
    """Run all generators and report combined results.

    Returns:
        Exit code: 0 if all pass, 1 if any fail.
    """
    argv = sys.argv[1:]
    generated_dir = _repo_root() / "plugin" / "help" / "generated"

    # Handle --stale flag (standalone check)
    if "--stale" in argv:
        return check_staleness(generated_dir)

    # Handle --coverage flag (standalone check)
    if "--coverage" in argv:
        return check_coverage(generated_dir)

    check = "--check" in argv
    mode = "Verifying" if check else "Generating"

    # Import new generators inline to avoid linter stripping
    from generate_faq_templates import main as generate_faqs
    from generate_note_templates import main as generate_notes
    from generate_task_templates import main as generate_tasks

    generators = [
        ("Error", generate_errors),
        ("Warning", generate_warnings),
        ("Tip", generate_tips),
        ("Reference", generate_references),
        ("Task", generate_tasks),
        ("FAQ", generate_faqs),
        ("Note", generate_notes),
        ("Cross-Links", build_cross_links),
    ]

    print(f"{'=' * 50}")
    print(f"  {mode} ALL documentation templates")
    print(f"{'=' * 50}\n")

    results: dict[str, int] = {}

    for name, gen_fn in generators:
        print(f"--- {name} templates ---\n")
        exit_code = gen_fn(argv)
        results[name] = exit_code
        print()

    # Build source manifest after generation (not in check mode)
    if not check:
        count = _write_manifest(generated_dir)
        print("--- Source Manifest ---\n")
        print(f"  [  OK] source_manifest.json: {count} entries")
        print()

    # Summary
    print(f"{'=' * 50}")
    print("  Summary")
    print(f"{'=' * 50}\n")

    total_ok = 0
    total_fail = 0
    for name, code in results.items():
        icon = "  OK" if code == 0 else "FAIL"
        print(f"  [{icon}] {name}")
        if code == 0:
            total_ok += 1
        else:
            total_fail += 1

    print(f"\n  Total: {total_ok} passed, {total_fail} failed")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
