"""Gate: file-op modules must reference a path-validation helper.
Enforces the contract's critical rule "ALWAYS validate file paths in
file operations" (collaboration contract; feature-lead-governance
principles draft, principle 4). Until 2026-07-29 this rule had no
mechanical enforcer — it relied on review discipline.
The scan (AST-based, so prose/comments can never false-positive):
- A module "does file ops" when it calls ``open()`` (builtin or the
  ``path.open(...)`` / ``Path.open`` attribute form) with a
  write-capable mode, ``.write_text()`` / ``.write_bytes()``, a
  mutating ``shutil`` function, or a mutating ``os`` function.
- A module "has validation" when any identifier it references
  contains both ``valid`` and ``path`` (matches
  ``_validate_file_path``, ``validate_file_path``, imports of
  ``attune.security.path_validation``, and equivalents).
- A module with file ops and no validation must hold an entry in
  ``ALLOWLIST`` below.
Fixing a failure, in preference order:
1. Route the path through
   ``attune.security.path_validation._validate_file_path`` (or an
   equivalent named helper) before the file op.
2. If every path the module writes is internal/derived (never
   user- or LLM-supplied), add the module to ``ALLOWLIST`` with the
   review that shipped it.
The allowlist is SHRINK-ONLY in spirit: it was seeded 2026-07-29 with
the 35 then-existing offenders so the gate lands green. A companion
test fails when an entry goes stale (module gained validation or
dropped its file ops) so the list ratchets down, never silently up.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "attune"
#: Attribute calls that write through a path-like receiver.
_WRITE_ATTRS = {"write_text", "write_bytes"}
#: shutil.<fn> calls that create, move, or destroy filesystem entries.
_SHUTIL_FUNCS = {"copy", "copy2", "copyfile", "copytree", "move", "rmtree"}
#: os.<fn> calls that destroy or rename filesystem entries.
_OS_FUNCS = {"remove", "unlink", "rename", "replace"}
#: tempfile.<fn> calls that CREATE a filesystem entry in a caller-supplied
#: ``dir=``. The atomic-write idiom (mkstemp + os.fdopen + Path.replace)
#: writes real files without ever calling ``.write_text``, so a scanner
#: that knows only the write-attr forms goes blind to those modules the
#: moment they adopt it — which is exactly what happened when the class-G1
#: sweep-fix landed. Detect the creation call itself.
_TEMPFILE_FUNCS = {"mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile"}
#: Modules with file ops and no path-validation reference, vetted at
#: seeding (2026-07-29): each writes only internal/derived paths
#: (state stores, telemetry sinks, generated docs). Remove entries as
#: modules adopt ``_validate_file_path``; add only with review.
#: Re-seeded 2026-08-19 when the scanner learned the ``path.open("a")``
#: attribute form (previously invisible): 11 writers became visible,
#: each reviewed as internal/derived-path only (JSONL ledgers,
#: telemetry sinks, hook metrics, env-gated debug dumps).
ALLOWLIST = frozenset(
    {
        "src/attune/authoring/fact_check/__init__.py",
        # Re-seeded 2026-08-21 with the atomic-write idiom. Reviewed:
        # NamedTemporaryFile with no caller-supplied dir, so the path is
        # entirely OS-chosen — nothing to validate.
        "src/attune/authoring/fact_check/tutorial_static_check.py",
        "src/attune/authoring/faithfulness/__init__.py",
        "src/attune/authoring/generator.py",
        "src/attune/authoring/manifest.py",
        "src/attune/authoring/polish.py",
        "src/attune/authoring/projector.py",
        "src/attune/authoring/spec_workflow.py",
        "src/attune/context/allocator.py",
        "src/attune/curator/cache.py",
        "src/attune/gates/envelope.py",
        "src/attune/gates/lifecycle/ledger.py",
        # Reviewed 2026-08-24: append-only session spend ledger. The
        # path is module-constructed (~/.attune/telemetry/) or an
        # operator env override (ATTUNE_SESSION_LEDGER_PATH), never
        # user- or LLM-supplied — same class as gates/envelope.py.
        "src/attune/gates/session_ledger.py",
        "src/attune/handoff/packet.py",
        "src/attune/hooks/scripts/worktree_path_guard.py",
        "src/attune/help/feedback.py",
        "src/attune/help/generator.py",
        "src/attune/help/manifest.py",
        "src/attune/help/session.py",
        "src/attune/memory/file_stash.py",
        "src/attune/memory/personal.py",
        "src/attune/memory/security/audit_logger.py",
        "src/attune/meta_workflows/cli_commands/analytics_commands.py",
        "src/attune/models/sdk_adapter.py",
        "src/attune/monitoring/alerts_cli.py",
        "src/attune/ops/dismiss_store.py",
        "src/attune/ops/health_snapshot.py",
        "src/attune/ops/ops_config_store.py",
        "src/attune/ops/pending_writes.py",
        "src/attune/ops/routes/specs.py",
        # Re-seeded 2026-08-21 when the scanner learned the atomic-write
        # idiom (tempfile.mkstemp + os.fdopen), previously invisible.
        # Reviewed: writes <attune_home>/ops/session_summaries/<id>.json.
        # NOTE: the <id> component is interpolated unvalidated — tracked
        # separately as a traversal question, not waved through here.
        "src/attune/ops/session_summary_cache.py",
        "src/attune/ops/sweep_results.py",
        "src/attune/orchestration/ghosts/worktree.py",
        "src/attune/pipeline_learner/decisions.py",
        "src/attune/pipeline_learner/scaffold.py",
        "src/attune/roundtable/countersign.py",
        "src/attune/roundtable/gate_triage.py",
        "src/attune/roundtable/role_telemetry.py",
        "src/attune/roundtable/triage_appendix.py",
        "src/attune/telemetry/help_tracker.py",
        "src/attune/telemetry/memory_events.py",
        "src/attune/telemetry/usage_ping.py",
        "src/attune/telemetry/usage_tracker.py",
        "src/attune/workflows/migration.py",
        "src/attune/workflows/progress_reporters.py",
        "src/attune/workflows/progressive/telemetry.py",
        "src/attune/workflows/suggestions.py",
    }
)


def _open_mode_is_write(call: ast.Call, mode_arg_index: int = 1) -> bool:
    """True when an ``open()`` call's mode string enables writing.

    ``mode_arg_index`` is 1 for builtin ``open(path, mode)`` and 0 for
    the ``path.open(mode)`` attribute form.
    """
    mode = None
    if len(call.args) > mode_arg_index and isinstance(call.args[mode_arg_index], ast.Constant):
        mode = call.args[mode_arg_index].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    if not isinstance(mode, str):
        return False
    return any(c in mode for c in "wax+")


def scan_source(source: str) -> tuple[list[str], bool]:
    """Return (file-op descriptions, has-validation-reference)."""
    tree = ast.parse(source)
    ops: list[str] = []
    has_validation = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name | ast.Attribute | ast.alias):
            ident = (
                node.id
                if isinstance(node, ast.Name)
                else node.attr if isinstance(node, ast.Attribute) else node.name
            )
            low = ident.lower()
            if "valid" in low and "path" in low:
                has_validation = True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                if _open_mode_is_write(node):
                    ops.append(f"open-for-write at line {node.lineno}")
            elif isinstance(func, ast.Attribute):
                if func.attr == "open":
                    if _open_mode_is_write(node, mode_arg_index=0):
                        ops.append(f".open()-for-write at line {node.lineno}")
                elif func.attr in _WRITE_ATTRS:
                    ops.append(f".{func.attr}() at line {node.lineno}")
                elif (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "shutil"
                    and func.attr in _SHUTIL_FUNCS
                ):
                    ops.append(f"shutil.{func.attr}() at line {node.lineno}")
                elif (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                    and func.attr in _OS_FUNCS
                ):
                    ops.append(f"os.{func.attr}() at line {node.lineno}")
                elif (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                    and func.attr == "fdopen"
                    and _open_mode_is_write(node, mode_arg_index=1)
                ):
                    ops.append(f"os.fdopen()-for-write at line {node.lineno}")
                elif (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "tempfile"
                    and func.attr in _TEMPFILE_FUNCS
                ):
                    ops.append(f"tempfile.{func.attr}() at line {node.lineno}")
    return ops, has_validation


def _current_offenders() -> dict[str, list[str]]:
    """Map repo-relative module path -> its unvalidated file ops."""
    offenders: dict[str, list[str]] = {}
    for py in sorted(SRC_ROOT.rglob("*.py")):
        try:
            ops, has_validation = scan_source(py.read_text(encoding="utf-8"))
        except SyntaxError:  # unparseable files fail other gates
            continue
        if ops and not has_validation:
            offenders[py.relative_to(REPO_ROOT).as_posix()] = ops
    return offenders


def test_no_new_unvalidated_file_op_modules() -> None:
    """Every file-op module validates paths or is allowlisted."""
    offenders = _current_offenders()
    new = {mod: ops for mod, ops in offenders.items() if mod not in ALLOWLIST}
    details = "\n".join(f"  {mod}: {', '.join(ops)}" for mod, ops in sorted(new.items()))
    assert not new, (
        "Modules perform file operations without referencing a "
        "path-validation helper (contract rule: ALWAYS validate file "
        "paths in file operations):\n"
        f"{details}\n"
        "Fix: route paths through "
        "attune.security.path_validation._validate_file_path before the "
        "file op, or (only for internal/derived paths) add the module "
        f"to ALLOWLIST in {Path(__file__).name} with review."
    )


def test_allowlist_entries_are_still_needed() -> None:
    """The allowlist ratchets down: stale entries must be removed."""
    offenders = _current_offenders()
    missing = sorted(mod for mod in ALLOWLIST if not (REPO_ROOT / mod).exists())
    assert not missing, f"ALLOWLIST entries for deleted modules — remove them: {missing}"
    stale = sorted(mod for mod in ALLOWLIST if mod not in offenders)
    assert not stale, (
        "ALLOWLIST entries no longer needed (module now validates paths "
        f"or dropped its file ops) — remove them to keep the ratchet: {stale}"
    )


# --- scanner self-tests: the true/false-positive pairs ---------------
def test_scanner_detects_write_open() -> None:
    ops, _ = scan_source('f = open(p, "w")\n')
    assert ops == ["open-for-write at line 1"]


def test_scanner_ignores_read_open() -> None:
    ops, _ = scan_source('f = open(p)\ng = open(p, "r")\n')
    assert ops == []


def test_scanner_detects_attribute_write_open() -> None:
    """The ``path.open("a")`` idiom is a write, same as builtin open."""
    ops, _ = scan_source('with p.open("a") as f:\n    f.write(x)\n')
    assert ops == [".open()-for-write at line 1"]


def test_scanner_ignores_attribute_read_open() -> None:
    ops, _ = scan_source('f = p.open()\ng = p.open("r")\n')
    assert ops == []


def test_scanner_detects_write_text_shutil_and_os_ops() -> None:
    source = "p.write_text(x)\nshutil.rmtree(d)\nos.remove(f)\n"
    ops, _ = scan_source(source)
    assert ops == [
        ".write_text() at line 1",
        "shutil.rmtree() at line 2",
        "os.remove() at line 3",
    ]


def test_scanner_detects_the_atomic_write_idiom() -> None:
    """mkstemp + os.fdopen writes a real file and must stay visible.

    The class-G1 sweep-fix replaced ``.write_text()`` with this idiom at
    ten sites. A scanner blind to it would have silently dropped six
    modules off the offender list while they still wrote files — the
    ratchet would then have demanded their allowlist entries be removed,
    making the gate assert something untrue.
    """
    source = 'fd, n = tempfile.mkstemp(dir=d)\nwith os.fdopen(fd, "w") as h:\n    h.write(x)\n'
    ops, _ = scan_source(source)
    assert ops == [
        "tempfile.mkstemp() at line 1",
        "os.fdopen()-for-write at line 2",
    ]


def test_scanner_ignores_fdopen_for_read() -> None:
    """A read-mode fdopen is not a write op."""
    ops, _ = scan_source('with os.fdopen(fd, "r") as h:\n    h.read()\n')
    assert ops == []


def test_scanner_validation_reference_clears_module() -> None:
    source = (
        "from attune.security.path_validation import _validate_file_path\n"
        '_validate_file_path(p)\nopen(p, "w")\n'
    )
    ops, has_validation = scan_source(source)
    assert ops and has_validation


def test_scanner_prose_mention_is_not_an_op() -> None:
    """Comments and docstrings never fire — the scan is AST-based."""
    source = '# open(p, "w") and shutil.rmtree here\n"""p.write_text(x)"""\n'
    ops, has_validation = scan_source(source)
    assert ops == [] and not has_validation
