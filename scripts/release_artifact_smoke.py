"""Clean-room artifact smoke gate (release-execute step 9).

Run INSIDE a pristine venv where attune-ai was installed from the built
artifact (wheel or sdist), with cwd OUTSIDE any repo checkout, e.g.:

    uv build --out-dir /tmp/dist
    python -m venv /tmp/smoke && /tmp/smoke/bin/pip install /tmp/dist/*.whl
    cd /tmp && env -i PATH=/usr/bin:/bin /tmp/smoke/bin/python \
        scripts/release_artifact_smoke.py <expected-version>

Why it exists (round-table q-16-release-reliability-001, unanimous,
2026-08-27): every other release receipt runs against the SOURCE TREE,
and editable installs can resurrect deleted modules from a sibling
checkout — so only an install of the built artifact into a clean venv
tests what a user actually gets. The removal baselines below are the
16.0.0 deletions; APPEND to them at future majors, never rewrite.

Post-publish rider: re-run this against the artifact installed FROM
PYPI, not just the locally built one.
"""

import importlib
import importlib.metadata as ilmd
import sys

failures: list[str] = []

# 0. Provenance: attune must resolve from site-packages, not a repo tree.
import attune  # noqa: E402

if "site-packages" not in (attune.__file__ or ""):
    failures.append(f"attune resolves outside site-packages: {attune.__file__}")

print(f"attune {attune.__version__} from {attune.__file__}")
EXPECTED = sys.argv[1] if len(sys.argv) > 1 else "16.0.0"
if attune.__version__ != EXPECTED:
    failures.append(f"version is {attune.__version__}, expected {EXPECTED}")

# 1. Deleted modules and shims must be genuinely gone.
DEAD = [
    "attune.discovery",
    "attune.pattern_cache",
    "attune.cache_stats",
    "attune.cache_monitor",
    "attune.vscode_bridge",
    "attune.template_engine",
    "attune.template_defs_basic",
    "attune.template_defs_web",
    "attune.templates",
    "attune.coordination",
    "attune.persistence",
    "attune.state_manager",
    "attune.redis_memory",
    "attune.redis_memory_storage",
    "attune.redis_memory_coordination",
    "attune.redis_memory_patterns",
]
for mod in DEAD:
    try:
        importlib.import_module(mod)
        failures.append(f"RESURRECTED: {mod} imports from the artifact")
    except ModuleNotFoundError:
        pass

# 2. Deleted aliases must raise AttributeError.
for modpath, attr in [
    ("attune.config", "AgentWorkflowConfig"),
    ("attune.config", "WorkflowMode"),
    ("attune.config.sections", "WorkflowConfig"),
    ("attune.agent_factory", "WorkflowConfig"),
]:
    m = importlib.import_module(modpath)
    try:
        getattr(m, attr)
        failures.append(f"ALIAS ALIVE: {modpath}.{attr}")
    except AttributeError:
        pass

# 3. Retained surfaces load: bundled attune_redis, memory backends seam.
import attune_redis  # noqa: E402,F401

eps = {ep.name for ep in ilmd.entry_points(group="attune.memory_backends")}
if eps != {"file", "redis"}:
    failures.append(f"memory_backends entry points: {sorted(eps)}")

# 4. Collapsed groups must be absent from the artifact metadata.
for group in ("attune.plugins", "attune.wizards", "attune.workflows"):
    stale = [
        ep.name for ep in ilmd.entry_points(group=group) if ep.dist and ep.dist.name == "attune-ai"
    ]
    if stale:
        failures.append(f"stale entry points in {group}: {stale}")

# 5. Behavioral enumeration parity (must match the source-tree receipt).
from attune.wizards.registry import list_wizards  # noqa: E402

wiz = sorted(w.wizard_id for w in list_wizards())
if wiz != ["debug", "refactor", "release-prep", "security", "test-gen"]:
    failures.append(f"wizards: {wiz}")

from attune.plugins.registry import get_global_registry  # noqa: E402

reg = get_global_registry()
plugs = sorted(reg._plugins)
if plugs != ["redis", "software"]:
    failures.append(f"plugins: {plugs}")

# 6. Public lazy exports repointed in the wheel.
for name in ("MetricsCollector", "PatternPersistence"):
    getattr(attune, name)
for gone in ("StateManager",):
    try:
        getattr(attune, gone)
        failures.append(f"export alive: attune.{gone}")
    except AttributeError:
        pass

print()
if failures:
    print("SMOKE FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("CLEAN-ROOM SMOKE: all checks passed")
