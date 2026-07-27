"""Front-loaded contract, scratch isolation, and sandbox-aware gates.

FABLE_SPEC_WORKFLOW_TODO items 3-5, layered around
:mod:`attune.authoring.spec_runner` (item 2):

- **Item 3** — assemble a :class:`DraftContract` BEFORE any external
  model call: one informed authorization (session-durable per packet
  class via :class:`SessionGrants`), scope resolved in one
  deterministic step (rich elicitation, else documented defaults —
  never a retry loop), and the generation strategy preselected from
  the ratified decision matrix, not chosen mid-flight.
- **Item 4** — :func:`scratch_packets` keeps prompt/reply packets in
  an isolated temp directory with guaranteed cleanup on success,
  failure, and interruption; :func:`review_surface_extras` asserts
  the repository review surface holds only intended artifacts.
- **Item 5** — :func:`plan_gate_boundary` probes the lifecycle-gate
  ledger path (``ATTUNE_HOME`` env -> ``~/.attune``, mirroring
  ``attune.gates.lifecycle.ledger``) BEFORE any gate runs and reports
  the selected execution boundary — host, isolated, or blocked with
  an actionable reason — so a sandbox restriction is discovered once,
  never spent as a failed gate attempt.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from attune.authoring.spec_runner import WHOLE_SPEC, Budgets, DocRequest

#: Decision-matrix bound (PR #1590): whole-spec is evidence-backed up
#: to five documents; larger requests split into <=5-file packets.
MAX_WHOLE_SPEC_DOCS = 5

HOST = "host"
ISOLATED = "isolated"
BLOCKED = "blocked"


# --------------------------------------------------------------------
# Item 3 — front-loaded workflow contract
# --------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeQuestion:
    """One scoping dimension with its documented default."""

    key: str
    question: str
    default: str


class SessionGrants:
    """Session-durable authorization grants, keyed by packet class.

    One informed authorization covers the scoped drafting sequence for
    that packet class; re-asking within the session is the failure
    mode this exists to prevent.
    """

    def __init__(self) -> None:
        self._grants: dict[str, str] = {}

    def grant(self, packet_class: str, *, note: str = "") -> None:
        """Record an informed authorization for ``packet_class``."""
        self._grants[packet_class] = note or datetime.now(timezone.utc).isoformat()

    def is_authorized(self, packet_class: str) -> bool:
        """True when this session already authorized the packet class."""
        return packet_class in self._grants


def resolve_scope(
    questions: Sequence[ScopeQuestion],
    elicit: Callable[[Sequence[ScopeQuestion]], dict[str, str]] | None = None,
) -> tuple[dict[str, str], str]:
    """Resolve scope in ONE deterministic step.

    Tries rich elicitation once when available; any failure or missing
    answer falls back immediately to the documented defaults — no
    retry loop, no second elicitation surface. Returns the answers and
    the source (``"elicited"``, ``"defaults"``, or ``"mixed"``).
    """
    defaults = {q.key: q.default for q in questions}
    if elicit is None:
        return defaults, "defaults"
    try:
        answers = elicit(questions)
    except Exception:  # noqa: BLE001 — any elicitation failure takes the one fallback path
        return defaults, "defaults"
    merged = {**defaults, **{k: v for k, v in answers.items() if k in defaults and v}}
    if merged == defaults:
        return defaults, "defaults"
    return merged, "elicited" if all(answers.get(q.key) for q in questions) else "mixed"


def preselect_packets(docs: Sequence[DocRequest]) -> list[list[DocRequest]]:
    """Split the request into whole-spec packets per the ratified matrix.

    <=5 documents ride as one whole-spec packet; larger requests chunk
    into <=5-file packets (unmeasured territory stays unentered). The
    per-document FALLBACK remains the runner's job at failure time —
    this is the launch-time strategy selection.
    """
    docs = list(docs)
    return [docs[i : i + MAX_WHOLE_SPEC_DOCS] for i in range(0, len(docs), MAX_WHOLE_SPEC_DOCS)]


@dataclass(frozen=True)
class DraftContract:
    """Everything item 3 requires settled BEFORE the first model call."""

    packet_class: str
    authorized: bool
    scope: dict[str, str]
    scope_source: str
    packets: list[list[DocRequest]]
    strategy: str = WHOLE_SPEC
    budgets: Budgets = field(default_factory=Budgets)

    @classmethod
    def assemble(
        cls,
        *,
        packet_class: str,
        grants: SessionGrants,
        docs: Sequence[DocRequest],
        questions: Sequence[ScopeQuestion] = (),
        elicit: Callable[[Sequence[ScopeQuestion]], dict[str, str]] | None = None,
        budgets: Budgets | None = None,
    ) -> DraftContract:
        """Front-load authorization check, scoping, and strategy."""
        scope, source = resolve_scope(questions, elicit)
        return cls(
            packet_class=packet_class,
            authorized=grants.is_authorized(packet_class),
            scope=scope,
            scope_source=source,
            packets=preselect_packets(docs),
            budgets=budgets or Budgets(),
        )

    def require_authorized(self) -> None:
        """Raise before any external invocation without a session grant."""
        if not self.authorized:
            raise PermissionError(
                f"packet class {self.packet_class!r} has no session authorization "
                "grant — present one informed external-data authorization "
                "before invoking the model (workflow todo item 3)"
            )


# --------------------------------------------------------------------
# Item 4 — scratch artifacts stay out of the review surface
# --------------------------------------------------------------------


@contextmanager
def scratch_packets(prefix: str = "attune-spec-scratch-") -> Iterator[Path]:
    """Isolated temp directory for prompt/reply packets.

    Lives under the system temp root — never the repository working
    tree — and is removed on success, exception, and interruption
    alike (the ``finally`` covers KeyboardInterrupt and timeouts).
    """
    scratch = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield scratch
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def review_surface_extras(repo_root: Path, intended: Sequence[str]) -> list[str]:
    """Paths in ``git status --short`` that are NOT intended artifacts.

    An empty return is the item-4 receipt: only the intended spec
    artifacts face review. Raises ``ValueError`` for a non-repository
    root rather than silently reporting a clean surface.
    """
    root = Path(repo_root).resolve()
    if not (root / ".git").exists():
        raise ValueError(f"{root} is not a git repository root")
    proc = subprocess.run(  # noqa: S603 — fixed argv, validated cwd
        ["git", "-C", str(root), "status", "--porcelain", "-uall"],
        capture_output=True,
        text=True,
        check=True,
    )
    wanted = {p.strip().rstrip("/") for p in intended}
    extras = []
    for line in proc.stdout.splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"').rstrip("/")
        if path not in wanted and not any(path.startswith(w + "/") for w in wanted):
            extras.append(path)
    return extras


# --------------------------------------------------------------------
# Item 5 — sandbox-aware lifecycle gates
# --------------------------------------------------------------------


@dataclass(frozen=True)
class GatePlan:
    """The selected gate execution boundary, decided before any gate runs."""

    boundary: str  # HOST | ISOLATED | BLOCKED
    attune_home: Path | None
    reason: str

    def env(self) -> dict[str, str]:
        """Environment overrides for running gates under this plan."""
        if self.boundary == BLOCKED or self.attune_home is None:
            raise RuntimeError(f"gate boundary is {self.boundary}: {self.reason}")
        return {"ATTUNE_HOME": str(self.attune_home)}


def _default_attune_home() -> Path:
    home = os.environ.get("ATTUNE_HOME")
    return Path(home).expanduser() if home else Path.home() / ".attune"


def _probe_writable(directory: Path) -> str | None:
    """None when ``directory`` accepts writes; else the error string."""
    probe = directory / f".write-probe-{uuid.uuid4().hex}"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return str(exc)
    return None


def plan_gate_boundary(
    *,
    require_real_ledger: bool = False,
    attune_home: Path | None = None,
    isolated_root: Path | None = None,
) -> GatePlan:
    """Pick the gate execution boundary BEFORE running any gate.

    Probes the ledger directory (``<attune_home>/ops/gates`` — the
    path ``attune.gates.lifecycle.ledger`` appends to) exactly once:

    - writable -> ``HOST``: gates run against the real ledger.
    - unwritable and the real receipt is required -> ``BLOCKED`` with
      an actionable reason (run host-side); the caller skips the gate
      instead of spending a failed attempt on a known restriction.
    - unwritable otherwise -> ``ISOLATED``: a writable ATTUNE_HOME
      under ``isolated_root`` (pass the item-4 scratch dir so cleanup
      rides its lifecycle; defaults to a fresh temp dir).
    """
    home = attune_home or _default_attune_home()
    error = _probe_writable(home / "ops" / "gates")
    if error is None:
        return GatePlan(HOST, home, "ledger directory is writable")
    if require_real_ledger:
        return GatePlan(
            BLOCKED,
            None,
            f"ledger under {home} is not writable ({error}) and the real "
            "receipt is required — run this gate through the trusted host "
            "boundary instead",
        )
    root = isolated_root or Path(tempfile.mkdtemp(prefix="attune-gate-home-"))
    isolated_home = root / "attune-home"
    isolated_home.mkdir(parents=True, exist_ok=True)
    return GatePlan(
        ISOLATED,
        isolated_home,
        f"ledger under {home} is not writable ({error}); gates run against "
        "an isolated ATTUNE_HOME",
    )
