"""Opt-in usage ping — the Phase 2 phone-home sync layer.

This is a *sync layer* over the local ``usage.jsonl`` written by
``UsageTracker`` (not a parallel pipeline): it reads local usage
records, maps each to a frozen anonymous payload, and best-effort POSTs
them to a collection endpoint.

Privacy contract (frozen — see ``docs/specs/usage-signals/phase2-design.md``):

- Ships OFF. Nothing transmits unless the user explicitly opts in.
- Payload is enumerated and frozen at schema v1 (:data:`PAYLOAD_KEYS`):
  package, version, anonymous rotating ``install_id``, event name
  (``workflow.<name>``), os, py, and timestamp. NEVER paths, code,
  prompts, args, filenames, cost/token/model data, or any free-text.
- Transport is fire-and-forget: short timeout, all errors swallowed —
  telemetry must never block, slow, or crash the CLI.
- ``DO_NOT_TRACK`` and ``ATTUNE_USAGE_PING`` env vars override config.

As of Phase 2b, :data:`DEFAULT_ENDPOINT` points at the live collection
endpoint, so an opted-in user transmits there by default. The default
remains OFF — opting in is still an explicit, deliberate choice.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import urllib.request
import uuid
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Payload schema version. Bump whenever :data:`PAYLOAD_KEYS` changes;
#: the freeze regression test asserts the exact set so the schema cannot
#: quietly grow free-text fields release-over-release.
PAYLOAD_SCHEMA_VERSION = 1

#: The EXACT, frozen set of keys a ping payload may contain. Anything
#: not listed here must never be transmitted.
PAYLOAD_KEYS = frozenset({"schema", "package", "version", "install_id", "event", "os", "py", "ts"})

#: Local-record fields that must NEVER appear in a payload. Documents
#: intent and backs a regression guard against accidental leakage.
FORBIDDEN_RECORD_FIELDS = frozenset(
    {
        "user_id",
        "cost",
        "tokens",
        "model",
        "provider",
        "tier",
        "stage",
        "duration_ms",
        "prompt_cache",
        "cache",
        "seq",
    }
)

#: Collection endpoint (Phase 2b). The ingest function is served by the
#: Next.js app at smartaimemory.com (``website/app/api/usage/route.ts``).
#: The TRAILING SLASH is required: the site runs ``trailingSlash: true``,
#: so ``/api/usage`` 308-redirects to ``/api/usage/`` and a redirected
#: POST is not reliably followed by ``urllib`` — point straight at the
#: canonical URL. Overridable via ``ATTUNE_USAGE_ENDPOINT`` (and the
#: whole ping is default-OFF, so this is only ever contacted by an
#: opted-in user).
DEFAULT_ENDPOINT = "https://smartaimemory.com/api/usage/"

#: Env values treated as "true" for flag variables.
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Cursor filename (stores the ISO timestamp of the last synced record).
_CURSOR_FILENAME = ".usage_ping_cursor"

_DEFAULT_TIMEOUT = 2.0
_DEFAULT_BATCH_SIZE = 100


def _env_truthy(value: str | None) -> bool:
    """Return True if an env value should be read as truthy."""
    return value is not None and value.strip().lower() in _TRUTHY


def _is_do_not_track(env: Mapping[str, str]) -> bool:
    """True if ``DO_NOT_TRACK`` is set to a non-empty, non-false value.

    Single source of truth for the opt-out predicate. Duplicating this
    check invites divergence, and divergence in a privacy opt-out is a
    privacy regression by definition.
    """
    dnt = env.get("DO_NOT_TRACK")
    return dnt is not None and dnt.strip().lower() not in {"", "0", "false"}


def is_enabled(usage_ping_flag: bool, env: Mapping[str, str] | None = None) -> bool:
    """Return whether usage pinging is enabled.

    Precedence (most authoritative first):

    1. ``DO_NOT_TRACK`` — if set to anything other than empty/0/false,
       pinging is OFF regardless of config (the opt-out always wins).
    2. ``ATTUNE_USAGE_PING`` — explicit env override (truthy enables).
    3. The persisted config flag.

    The default is OFF.

    Args:
        usage_ping_flag: The persisted ``TelemetryConfig.usage_ping``.
        env: Environment mapping (defaults to ``os.environ``).

    Returns:
        True if pings should be sent.
    """
    env = os.environ if env is None else env
    if _is_do_not_track(env):
        return False
    override = env.get("ATTUNE_USAGE_PING")
    if override is not None:
        return _env_truthy(override)
    return bool(usage_ping_flag)


def resolve_endpoint(env: Mapping[str, str] | None = None) -> str:
    """Return the collection endpoint (env override or default)."""
    env = os.environ if env is None else env
    return (env.get("ATTUNE_USAGE_ENDPOINT") or DEFAULT_ENDPOINT).strip()


def new_install_id() -> str:
    """Mint a fresh anonymous, rotating install identifier (UUIDv4)."""
    return str(uuid.uuid4())


def _platform_os() -> str:
    """Return a coarse platform name (e.g. 'darwin', 'linux', 'windows')."""
    return platform.system().lower()


def _platform_py() -> str:
    """Return the major.minor Python version (e.g. '3.12')."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def build_payload(
    record: Mapping[str, Any],
    *,
    install_id: str,
    version: str,
    os_name: str | None = None,
    py_version: str | None = None,
) -> dict[str, Any]:
    """Map a local usage record to the frozen anonymous ping payload.

    Only the workflow NAME and timestamp are taken from the record; all
    cost/token/model/user fields are dropped by construction. The result
    contains exactly :data:`PAYLOAD_KEYS`.

    Args:
        record: A single local ``usage.jsonl`` entry.
        install_id: Rotating anonymous install identifier.
        version: attune-ai package version.
        os_name: Override platform name (defaults to the live platform).
        py_version: Override Python version (defaults to the live one).

    Returns:
        A payload dict whose keys are exactly :data:`PAYLOAD_KEYS`.
    """
    workflow = str(record.get("workflow") or "unknown")
    return {
        "schema": PAYLOAD_SCHEMA_VERSION,
        "package": "attune-ai",
        "version": version,
        "install_id": install_id,
        "event": f"workflow.{workflow}",
        "os": os_name if os_name is not None else _platform_os(),
        "py": py_version if py_version is not None else _platform_py(),
        "ts": str(record.get("ts") or ""),
    }


def _urllib_post(url: str, batch: list[dict[str, Any]], timeout: float) -> bool:
    """POST a batch of payloads as JSON. Returns True on a 2xx response."""
    data = json.dumps({"events": batch}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 (scheme validated by caller)
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "attune-ai-usage-ping",
        },
    )
    # nosec B310: sync() validates the scheme is http/https before calling.
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 # nosec B310
        status = getattr(resp, "status", None) or resp.getcode()
        return 200 <= int(status) < 300


def sync(
    records: Iterable[Mapping[str, Any]],
    *,
    endpoint: str,
    install_id: str,
    version: str,
    timeout: float = _DEFAULT_TIMEOUT,
    batch_size: int = _DEFAULT_BATCH_SIZE,
    poster: Callable[[str, list[dict[str, Any]], float], bool] = _urllib_post,
) -> int:
    """Best-effort transmit payloads built from ``records``.

    Fire-and-forget: this never raises. On any failure it returns the
    count of records confirmed sent so far, so the caller can leave its
    cursor parked before the first unsent record and retry next run.

    Records are sent in iteration order; callers that need an accurate
    resume cursor should pass them sorted by timestamp.

    Args:
        records: Local usage records to transmit.
        endpoint: Collection URL (must be http/https; empty = no-op).
        install_id: Rotating anonymous install identifier.
        version: attune-ai package version.
        timeout: Per-request timeout in seconds.
        batch_size: Max payloads per POST.
        poster: Injectable transport (defaults to a urllib POST).

    Returns:
        Number of records confirmed transmitted (a 2xx response).
    """
    if not endpoint:
        return 0
    if not (endpoint.startswith("https://") or endpoint.startswith("http://")):
        logger.debug("usage-ping: endpoint scheme not allowed: %r", endpoint)
        return 0

    sent = 0
    batch: list[dict[str, Any]] = []
    try:
        for record in records:
            batch.append(build_payload(record, install_id=install_id, version=version))
            if len(batch) >= batch_size:
                if not poster(endpoint, batch, timeout):
                    return sent
                sent += len(batch)
                batch = []
        if batch and poster(endpoint, batch, timeout):
            sent += len(batch)
        return sent
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry must never raise into the caller.
        logger.debug("usage-ping: sync failed", exc_info=True)
        return sent


def read_cursor(telemetry_dir: Path) -> str:
    """Return the last-synced ISO timestamp, or '' if none/unreadable."""
    try:
        return (telemetry_dir / _CURSOR_FILENAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_cursor(telemetry_dir: Path, ts: str) -> None:
    """Persist the last-synced ISO timestamp (best-effort)."""
    try:
        (telemetry_dir / _CURSOR_FILENAME).write_text(ts, encoding="utf-8")
    except OSError:
        logger.debug("usage-ping: could not write cursor")


def records_since(telemetry_dir: Path, cursor_ts: str) -> list[dict[str, Any]]:
    """Return local usage records newer than ``cursor_ts``, sorted by ts.

    Reads every ``usage*.jsonl`` (current + rotated) so the cursor
    survives file rotation. ISO-8601 UTC timestamps sort lexically =
    chronologically. Malformed lines are skipped.
    """
    out: list[dict[str, Any]] = []
    for path in sorted(telemetry_dir.glob("usage*.jsonl")):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = str(rec.get("ts") or "")
                    if ts and ts > cursor_ts:
                        out.append(rec)
        except OSError:
            continue
    out.sort(key=lambda r: str(r.get("ts") or ""))
    return out


def run_sync(
    config: Any,
    *,
    telemetry_dir: Path | None = None,
    version: str | None = None,
    env: Mapping[str, str] | None = None,
    poster: Callable[[str, list[dict[str, Any]], float], bool] = _urllib_post,
) -> int:
    """Orchestrate one sync pass: gate, read, transmit, advance cursor.

    Returns the number of records transmitted (0 if disabled, no endpoint,
    no install id, or nothing new). Never raises.

    Args:
        config: A ``UnifiedConfig`` (uses ``config.telemetry``).
        telemetry_dir: Override directory (defaults to ~/.attune/telemetry).
        version: Override package version (defaults to ``attune.__version__``).
        env: Environment mapping (defaults to ``os.environ``).
        poster: Injectable transport.
    """
    env = os.environ if env is None else env
    tele = config.telemetry
    if not is_enabled(tele.usage_ping, env):
        return 0
    if not tele.install_id:
        return 0
    endpoint = resolve_endpoint(env)
    if not endpoint:
        return 0

    if telemetry_dir is None:
        telemetry_dir = Path("~/.attune/telemetry").expanduser()
    if version is None:
        from attune import __version__ as version

    cursor = read_cursor(telemetry_dir)
    records = records_since(telemetry_dir, cursor)
    if not records:
        return 0

    sent = sync(
        records,
        endpoint=endpoint,
        install_id=tele.install_id,
        version=version,
        poster=poster,
    )
    if sent > 0:
        write_cursor(telemetry_dir, str(records[sent - 1].get("ts") or cursor))
    return sent


def run_sync_at_exit(
    *,
    env: Mapping[str, str] | None = None,
    poster: Callable[[str, list[dict[str, Any]], float], bool] = _urllib_post,
) -> int:
    """Best-effort sync entry point for the atexit / Stop trigger.

    Self-gating and never raises. Applies the cheap short-circuits (hard
    env opt-out, no endpoint, no user config on disk) BEFORE loading any
    config, so an opted-out user pays nothing at process exit beyond a
    couple of dict lookups. When it does proceed it defers entirely to
    :func:`run_sync`, which re-checks enablement / install id / endpoint.

    Opt-in state lives ONLY in the user config (``~/.attune/config.json``),
    never a discovered project config — see :func:`_open_user_config`.

    Returns:
        Number of records transmitted (0 when disabled or nothing new).
    """
    try:
        env = os.environ if env is None else env
        # Hard opt-outs short-circuit before touching disk.
        if _is_do_not_track(env):
            return 0
        override = env.get("ATTUNE_USAGE_PING")
        if override is not None and not _env_truthy(override):
            return 0
        # No endpoint wired -> nothing to do (avoids a config load).
        if not resolve_endpoint(env):
            return 0

        from attune.config.loader import ConfigLoader

        path = ConfigLoader.get_default_config_path()
        # A user who never created a config never opted in — don't create
        # one (or even load defaults) at exit.
        if not path.exists():
            return 0
        config = ConfigLoader(config_path=path).load()
        return run_sync(config, env=env, poster=poster)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry must never raise into process teardown.
        logger.debug("usage-ping: run_sync_at_exit failed", exc_info=True)
        return 0


def example_payload(
    config: Any,
    *,
    version: str | None = None,
    os_name: str | None = None,
    py_version: str | None = None,
) -> dict[str, Any]:
    """Return the exact payload shape that would be transmitted.

    Used by ``attune telemetry status`` so a user can audit precisely
    what leaves their machine before opting in.
    """
    if version is None:
        from attune import __version__ as version
    return build_payload(
        {"workflow": "<example>", "ts": "<timestamp>"},
        install_id=config.telemetry.install_id or "<minted-on-opt-in>",
        version=version,
        os_name=os_name,
        py_version=py_version,
    )


def _open_user_config(loader: Any) -> tuple[Any, Any, Path | None]:
    """Return ``(loader, config, save_path)`` targeting the USER config.

    Opt-in state (the flag + anonymous install id) is per-user and
    per-machine, so it must NEVER be written to a discovered
    project-local ``attune.config.json`` (that would let a user commit
    their install id, or ``usage_ping=true`` for everyone who clones).
    When no loader is injected we target ``~/.attune/config.json``
    explicitly, starting from defaults if it does not exist yet.

    A non-None ``loader`` (tests) is used as-is with ``save_path=None``.
    """
    if loader is not None:
        return loader, loader.load(), None

    from attune.config.loader import ConfigLoader
    from attune.config.unified import UnifiedConfig

    home = ConfigLoader.get_default_config_path()
    if home.exists():
        loader = ConfigLoader(config_path=home)
        return loader, loader.load(), home
    return ConfigLoader(), UnifiedConfig(), home


def enable(loader: Any = None) -> str:
    """Opt in to usage pinging. Mints an install id if absent.

    Writes to the user config (~/.attune/config.json). Returns the
    (anonymous) install id.
    """
    loader, config, save_path = _open_user_config(loader)
    config.telemetry.usage_ping = True
    config.telemetry.usage_ping_consented = True
    if not config.telemetry.install_id:
        config.telemetry.install_id = new_install_id()
    loader.save(config, save_path)
    return config.telemetry.install_id


def disable(loader: Any = None) -> None:
    """Opt out of usage pinging (records the explicit choice)."""
    loader, config, save_path = _open_user_config(loader)
    config.telemetry.usage_ping = False
    config.telemetry.usage_ping_consented = True
    loader.save(config, save_path)


def reset_install_id(loader: Any = None) -> str:
    """Rotate the anonymous install id to a fresh value. Returns it."""
    loader, config, save_path = _open_user_config(loader)
    config.telemetry.install_id = new_install_id()
    loader.save(config, save_path)
    return config.telemetry.install_id


# The one-time, interactive first-run consent notice. Kept verbatim so the
# wording is reviewable in one place; printed only in an interactive
# terminal (see :func:`maybe_prompt_consent`).
_CONSENT_NOTICE = (
    "\nattune-ai can share anonymous usage to help improve it — only which\n"
    "workflows you run, plus the version, your OS, and Python version.\n"
    "Never code, paths, prompts, or personal data. Off by default.\n\n"
    "Enable anonymous usage sharing? [y/N]: "
)


def _is_interactive() -> bool:
    """True only when BOTH stdin and stdout are real terminals.

    Guards the consent prompt so it never hangs or nags a non-interactive
    run (CI, pipes, scripts, redirected output).
    """
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except (OSError, ValueError):  # closed/!detached streams
        return False


def maybe_prompt_consent(
    loader: Any = None,
    env: Mapping[str, str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
) -> bool | None:
    """Ask once, interactively, whether to enable the anonymous usage ping.

    The opt-in lever for usage-signals: fires at most once per user
    (gated on :attr:`TelemetryConfig.usage_ping_consented`), and only in
    an interactive terminal where the user has not already expressed a
    preference via ``DO_NOT_TRACK`` or ``ATTUNE_USAGE_PING``. "Yes" opts
    in (minting an install id); anything else records an explicit opt-out.
    Either answer sets ``usage_ping_consented`` so the prompt never
    re-appears.

    Best-effort and silent: it never raises into the caller and never
    blocks a non-interactive run. When it skips for a *transient* reason
    (non-interactive, ``DO_NOT_TRACK`` set, an aborted prompt) it does
    NOT record consent, so a later interactive run can still ask.

    Args:
        loader: Optional config loader (tests inject one); defaults to the
            user config at ``~/.attune/config.json``.
        env: Environment mapping (defaults to ``os.environ``).
        input_fn: Injectable input function (tests).

    Returns:
        True if the user opted in, False if they opted out, or None if no
        prompt was shown (skipped).
    """
    env = os.environ if env is None else env

    # An explicit env signal already settles it — never prompt over one.
    if _is_do_not_track(env):
        return None
    if env.get("ATTUNE_USAGE_PING") is not None:
        return None

    if not _is_interactive():
        return None

    try:
        cfg_loader, config, _ = _open_user_config(loader)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry consent must never break the CLI. If the
        # config can't be read, skip quietly (no consent recorded).
        logger.debug("usage-ping: consent prompt skipped (config load failed)", exc_info=True)
        return None

    if config.telemetry.usage_ping_consented:
        return None

    try:
        answer = input_fn(_CONSENT_NOTICE).strip().lower()
    except (EOFError, KeyboardInterrupt):
        # Aborted prompt = "not now": do NOT record consent so a future
        # interactive run can ask again.
        print()
        return None

    try:
        if answer in {"y", "yes"}:
            enable(cfg_loader)
            print(
                "Thanks! Anonymous usage sharing is on. "
                "Disable anytime with `attune telemetry disable`.\n"
            )
            return True
        disable(cfg_loader)
        print("No problem — staying off. " "Enable anytime with `attune telemetry enable`.\n")
        return False
    except Exception:  # noqa: BLE001
        # INTENTIONAL: a persist failure must not crash the CLI.
        logger.debug("usage-ping: consent prompt persist failed", exc_info=True)
        return None
