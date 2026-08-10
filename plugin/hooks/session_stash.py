#!/usr/bin/env python
"""Stop-hook session-stash — capture reusable findings once per session.

The ``Stop`` event fires on every turn, so this hook acts ONCE per
session (a per-session sentinel) and only after the transcript has
accumulated meaningful content (a utilization gate), so it snapshots a
substantive session rather than an empty opening turn.

Flow (all best-effort, never blocks a stop):

1. Read the session transcript tail.
2. Extract <=5 structured findings via a LOCAL Ollama model
   (``llama3.1:8b`` by default); degrade to a cheap heuristic marker
   scan when Ollama is unavailable.
3. Stash each finding through ``attune.memory.session_stash.stash_entry``
   — which runs the PII/secrets gate and writes to the searchable
   backend (file by default, AMS when connected).
4. Prune expired findings once.

When findings are stashed, the hook also emits a compact summary on
stdout as Stop-hook ``additionalContext`` (Claude Code >= 2.1.163) so the
captured insights surface into the CURRENT session's next turn — not only
on disk for the next ``/recall``. On older Claude Code the JSON line is
ignored (stdout was previously discarded), so this is purely additive.

Tunables (env): ``ATTUNE_MEMORY_STASH`` (set ``0`` to disable),
``ATTUNE_MEMORY_STASH_MIN_UTIL`` (gate, default 0.05),
``ATTUNE_MEMORY_OLLAMA_MODEL`` (default ``llama3.1:8b``),
``ATTUNE_MEMORY_OLLAMA_URL`` (default ``http://localhost:11434``),
``ATTUNE_MEMORY_STASH_TIMEOUT`` (LLM timeout secs, default 40 — a cold
llama3.1:8b can exceed a tighter cap and starve extraction),
``ATTUNE_MEMORY_STASH_CONTEXT`` (set ``0`` to suppress the
``additionalContext`` emission while still stashing to disk).

Each stash is logged to ``~/.attune/telemetry/memory_events.jsonl``
(findings/written counts, extractor, injected size; see
``_memory_telemetry``) so the capture side is measurable too.

Exit 0 always.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path

# Force utf-8 on stdout/stderr (Windows cp1252 would crash on em-dash/
# emoji, caught by the outer try/except -> silent breakage).
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

# Reuse the transcript size proxy + sentinel dir from the existing hooks.
try:
    from _state import _sentinel_dir  # type: ignore[attr-defined]
    from _transcript_size import estimate_utilization
except Exception:  # noqa: BLE001 — hook must never crash a session
    _sentinel_dir = None  # type: ignore[assignment]
    estimate_utilization = None  # type: ignore[assignment]

try:
    from _memory_telemetry import log_memory_event
except Exception:  # noqa: BLE001 — telemetry is optional, never load-bearing

    def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
        return


_VALID_TYPES = {"decision", "pattern", "bug", "reference", "note"}
_MAX_FINDINGS = 5

# memory-security-hardening R5 — discard-on-malformed. A raw finding becomes
# durable, re-injectable text, so extractor output carrying STRUCTURAL injection
# machinery is dropped at extraction (not truncated-and-kept): control
# characters, frontmatter delimiter lines (`---`, the break-out-into-YAML
# vector if a finding is ever promoted into a curated `.md`), and role/tool-call
# delimiter tokens. This mirrors provenance's high-signal patterns without
# importing it — the Stop hook stays self-contained and resilient. Note: prose
# like "ignore previous instructions" is deliberately NOT dropped here — R1
# flags it at recall, and dropping it would lose legitimate findings ABOUT
# injection.
_MALFORMED_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MALFORMED_FRONTMATTER_RE = re.compile(r"(?m)^\s*---+\s*$")
_MALFORMED_ROLE_TOOL_RE = re.compile(
    r"<\|(?:im_start|im_end|system|assistant|user)\|>"  # ChatML
    r"|</?(?:system|human|assistant)>"  # Anthropic/Claude XML
    r"|\[/?INST\]|<<SYS>>"  # Llama / Mistral
    r"|</?(?:tool_call|function_call|invoke|antml:invoke)\b",  # tool machinery
    re.I,
)


def _is_malformed(content: str) -> bool:
    """True if a finding carries structural injection machinery (R5)."""
    return bool(
        _MALFORMED_CONTROL_RE.search(content)
        or _MALFORMED_FRONTMATTER_RE.search(content)
        or _MALFORMED_ROLE_TOOL_RE.search(content)
    )


_TAIL_CHARS = 8_000  # transcript tail handed to the extractor (smaller = faster LLM)
# Calibrated 2026-06-11: the estimator counts only user/assistant message-body
# chars (tool results excluded), so a substantive tool-heavy session plateaus
# far below the old 0.30 gate — a real 1.2 MB transcript measured 0.18 and
# never stashed. 0.05 (~10k message-body tokens) separates trivial sessions
# from substantive ones. Receipts:
# docs/specs/just-in-time-recall/recall-loop-triage-2026-06-11.md
_DEFAULT_MIN_UTIL = 0.05


def _enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_STASH", "1").strip() not in {"0", "false", "no"}


def _diag(msg: str) -> None:
    """Append a one-line diagnostic to ``stash.log`` in the sentinel dir.

    Stop-hook stdout/stderr are discarded on exit 0, so this file is the only
    forensic trail for "the hook ran but nothing was stored" — the failure
    class the 2026-06-11 triage had to reconstruct from scratch. Best-effort:
    never raises. The sentinel dir is env-overridable
    (``ATTUNE_AI_SENTINEL_DIR``), so tests redirect automatically.
    """
    if _sentinel_dir is None:
        return
    try:
        from datetime import datetime

        d = _sentinel_dir()
        d.mkdir(parents=True, exist_ok=True)
        with (d / "stash.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: diagnostics must never break the host session.
        pass


def _stash_sentinel(session_id: str | None) -> Path | None:
    if _sentinel_dir is None:
        return None
    safe = "unknown"
    if session_id:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:64] or "unknown"
    return _sentinel_dir() / f".stash-done-{safe}"


def _read_transcript_tail(transcript_path: str | None, max_chars: int = _TAIL_CHARS) -> str:
    """Return the human-readable tail of the session transcript.

    Walks the JSONL user/assistant turns, extracts text, and returns the
    last ``max_chars`` characters. Tolerant of malformed lines / missing
    files; never raises.
    """
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_file():
        return ""
    chunks: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                message = record.get("message")
                content = (
                    message.get("content") if isinstance(message, dict) else record.get("content")
                )
                role = (
                    (message or {}).get("role")
                    if isinstance(message, dict)
                    else record.get("role") or record.get("type")
                )
                text = _text_of(content)
                if text:
                    chunks.append(f"{role or '?'}: {text}")
    except OSError:
        return ""
    joined = "\n".join(chunks)
    # Collapse runs of marker-only lines (each behind its `role: ` prefix)
    # left by tool-heavy stretches, so they don't eat the char budget
    # (R1, stash-extractor-provenance).
    marker = re.escape(_OMITTED_MARKER)
    joined = re.sub(
        rf"(?:^\S*: {marker}\s*$\n?){{2,}}",
        f"{_OMITTED_MARKER}\n",
        joined,
        flags=re.MULTILINE,
    )
    return joined[-max_chars:]


#: Replaces tool_result/tool_use block content in the extractor's tail.
#: Tool results are user-ROLE messages in the transcript JSONL, so
#: without this filter every file the assistant read entered the tail as
#: `user: <file contents>` — mislabeled as user speech, and the source
#: of the 2026-07-05 garbled-stash incident (#1263). See
#: docs/specs/stash-extractor-provenance/.
_OMITTED_MARKER = "[tool output omitted]"
_AMBIENT_BLOCK_TYPES = {"tool_result", "tool_use"}


def _text_of(content: object) -> str:
    """Collect the ROLE-FAITHFUL string text from a transcript message body.

    Recursive over the block structure; ``tool_result``/``tool_use``
    blocks contribute only an omission marker (R1) — their content is
    context the session saw, not something a participant said.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(_text_of(p) for p in content).strip()
    if isinstance(content, dict):
        if content.get("type") in _AMBIENT_BLOCK_TYPES:
            return _OMITTED_MARKER
        parts: list[str] = []
        t = content.get("text")
        if isinstance(t, str):
            parts.append(t)
        nested = content.get("content")
        if nested is not None:
            parts.append(_text_of(nested))
        return " ".join(p for p in parts if p).strip()
    return ""


def _extract_via_ollama(text: str) -> list[dict] | None:
    """Ask a local Ollama model for <=5 findings. None when unavailable."""
    base = os.environ.get("ATTUNE_MEMORY_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("ATTUNE_MEMORY_OLLAMA_MODEL", "llama3.1:8b")
    try:
        timeout = float(os.environ.get("ATTUNE_MEMORY_STASH_TIMEOUT", "40"))
    except ValueError:
        timeout = 40.0
    if _refs_v2_enabled():
        # Design D-2: v2 requests a refs list and STOPS requesting
        # source_ref (deprecated in v2; v1 rows are never rewritten).
        shape = '{"findings": [{"type": "...", "content": "...", "confidence": 0.9, "refs": []}]}'
        ref_clause = (
            '- refs: 0-3 entries "kind:value" (kinds: file:<path>, pr:<number>,\n'
            "  spec:<slug>). Attach a ref ONLY if the finding is ABOUT that\n"
            "  artifact — if removing the ref would make the finding\n"
            "  unverifiable. Artifacts that merely appeared in the session do\n"
            "  not qualify; a convenience reference is a defect. refs: [] is\n"
            "  a correct and common answer. Write the finding first, refs\n"
            "  second — never let refs shorten the finding.\n"
        )
    else:
        shape = (
            '{"findings": [{"type": "...", "content": "...", "confidence": 0.9,'
            ' "source_ref": "optional"}]}'
        )
        ref_clause = (
            "- source_ref is OPTIONAL: a short file path or locator the finding is\n"
            "  about (omit when none applies; never invent one).\n"
        )
    prompt = (
        "You are extracting durable memory from a coding session transcript.\n"
        f"Return ONLY JSON of the form {shape}.\n"
        "Rules:\n"
        "- At most 5 findings; fewer is better. Skip chit-chat and routine steps.\n"
        "- Each finding is a single reusable insight worth recalling next session.\n"
        "- type is one of: decision, pattern, bug, reference, note.\n"
        "- content is one concise sentence, <= 280 chars, no secrets/paths-as-secrets.\n"
        "- confidence is REQUIRED: a number 0.0-1.0 — how certain you are this\n"
        "  was asserted in the session AND is worth recalling. Findings without\n"
        "  it are discarded.\n"
        f"{ref_clause}"
        "- PROVENANCE: extract only what the ASSISTANT concluded or the USER\n"
        "  decided IN THIS SESSION. Never restate file contents, docs, or\n"
        "  tool output the session merely read — reading a claim is not\n"
        "  finding it. When unsure whether the session asserted it, skip it.\n\n"
        f"TRANSCRIPT TAIL:\n{text}\n"
    )
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — localhost
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError):
        return None  # Ollama not running / model missing / timeout -> heuristic fallback
    raw = body.get("response") if isinstance(body, dict) else None
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    findings = parsed.get("findings") if isinstance(parsed, dict) else None
    typed = _parse_typed_findings(findings)
    # Return None (not []) when nothing survives the typed parse so the caller
    # falls back to the heuristic — an empty or all-discarded Ollama answer
    # shouldn't starve extraction (R5#2: discard on mismatch, keep fallback).
    return typed or None


#: R5#2 — a source_ref is a short locator, not a payload channel.
_MAX_SOURCE_REF_CHARS = 200

# --- refs v2 (memory-claim-verification D9 / design.md, flag-gated) ------
#
# The ENTIRE v2 path — prompt delta AND binder — ships default-OFF behind
# ATTUNE_MEMORY_REFS_V2; the spec's T4 gate flips it (design D-3). With the
# flag off this hook behaves byte-for-byte as v1.

#: D-2: at most three refs per finding — more must pick the strongest.
_MAX_REFS = 3
#: The BINDER's kind allowlist. Deliberately not enforced by the parser:
#: an unknown kind must reach the binder to be stored rejected:bad_kind
#: (design D-2/D-3 — a parser allowlist would eat that evaluation surface).
_REF_KINDS = {"file", "pr", "spec"}
#: Parser-side SYNTAX check only: word:value shape.
_REF_SYNTAX_RE = re.compile(r"^[a-z][a-z0-9_-]*:.+$")
#: Stamped on every v2 finding (design D-4 corpus versioning).
_REFS_PROMPT_VERSION = "refs-v1"

#: Universe-derivation patterns over tool_use command strings (design D-3;
#: seeded from scripts/probe_ref_binding.py — the probe now imports these).
_UNIVERSE_PR_RE = re.compile(
    r"(?:#|pull/)(\d{2,6})\b"
    # `gh pr <subcommand> 1234` operates directly on that PR (codex lane).
    r"|\bgh pr (?:view|merge|edit|checks|diff|review|close|reopen|comment|ready)"
    r"\s+(?:--\S+\s+)*(\d{2,6})\b"
)
#: Slashed paths at any depth (incl. dot-prefixed segments like .github/),
#: plus well-known root-level files — command text only (codex lane).
_UNIVERSE_FILE_RE = re.compile(
    r"(?<![\w./-])((?:[\w.-]+/)+[\w.-]+\.\w+)"
    r"|(?:^|[\s'\"])((?:pyproject\.toml|README\.md|CHANGELOG\.md|uv\.lock|"
    r"pytest\.ini|codecov\.yml|Makefile|\.pre-commit-config\.yaml|"
    r"\.secrets\.baseline))\b"
)
_UNIVERSE_SPEC_RE = re.compile(r"docs/specs/([\w-]+)")


def _first_group(groups: str | tuple[str, ...]) -> str:
    """First non-empty capture from a multi-alternative pattern match."""
    if isinstance(groups, str):
        return groups
    return next((g for g in groups if g), "")


def _refs_v2_enabled() -> bool:
    """True when the v2 refs path is switched on (default off — T4 gate)."""
    return os.environ.get("ATTUNE_MEMORY_REFS_V2", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_typed_findings(items: object) -> list[dict]:
    """R5#2: strict typed-schema parse of extractor (LLM) output.

    Per-finding discard-on-mismatch, fail closed — never coerce: wrong shape,
    unknown ``type``, non-string/empty ``content``, missing or out-of-range
    ``confidence``, or a ``source_ref`` that is non-string, over-long, or
    carries injection machinery drops the WHOLE finding. The heuristic
    fallback path never runs through this parse (its findings carry no
    confidence by design).
    """
    if not isinstance(items, list):
        return []
    typed: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        confidence = item.get("confidence")
        if item.get("type") not in _VALID_TYPES:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        # bool is an int subclass — reject it explicitly.
        if isinstance(confidence, bool) or not isinstance(confidence, int | float):
            continue
        if not 0.0 <= float(confidence) <= 1.0:
            continue
        finding = {
            "type": item["type"],
            "content": content,
            "confidence": round(float(confidence), 3),
        }
        ref = item.get("source_ref")
        if ref is not None:
            if not isinstance(ref, str) or len(ref) > _MAX_SOURCE_REF_CHARS or _is_malformed(ref):
                continue  # a malformed ref poisons the finding — drop it whole
            if ref.strip():
                finding["source_ref"] = ref.strip()
        refs = item.get("refs")
        if isinstance(refs, list):
            # Design D-2: SYNTAX + R5#2 string discipline only, ITEM-level
            # drop — an over-eager ref must never cost a good finding. Kind
            # validation is the BINDER's (rejected:bad_kind), not ours. A
            # refs field whose every item drops yields [] (explicit-unbound);
            # a NON-list refs is treated as absent so a malformed shape
            # cannot masquerade as the explicit-unbound signal.
            kept: list[str] = []
            for r in refs:
                if not isinstance(r, str):
                    continue
                r = r.strip()
                if not r or len(r) > _MAX_SOURCE_REF_CHARS or _is_malformed(r):
                    continue
                if not _REF_SYNTAX_RE.match(r):
                    continue
                if r not in kept:
                    kept.append(r)
            finding["refs"] = kept[:_MAX_REFS]
        typed.append(finding)
    return typed


_MARKER_RE = re.compile(
    r"\b(lesson|TIL|gotcha|decided|decision|bug|root cause|pattern|fix(?:ed)?|"
    r"learned|insight|takeaway)\b",
    re.IGNORECASE,
)

#: Lines that match a marker but are mechanical noise, not insights:
#: git-log / commit lines (short hex prefix, conventional-commit prefix, or a
#: PR/issue ref). These dominate a transcript tail full of `git log` output
#: and otherwise crowd out real findings.
_NOISE_RE = re.compile(
    r"^[0-9a-f]{7,40}\s"  # leading commit hash
    r"|^(?:feat|fix|chore|docs|test|refactor|ci|build|style|perf)(?:\([^)]*\))?!?:"  # conv-commit
    r"|\(#\d+\)",  # PR/issue reference
    re.IGNORECASE,
)


def _extract_heuristic(text: str) -> list[dict]:
    """Cheap fallback: surface marker-bearing lines as ``note`` findings.

    Filters out git-log / commit-message noise (see :data:`_NOISE_RE`) so the
    fallback yields prose insights rather than scraped commit lines.
    """
    out: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip(" -*#>\t")
        if len(line) < 20 or len(line) > 280:
            continue
        if not _MARKER_RE.search(line):
            continue
        if _NOISE_RE.search(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"type": "note", "content": line})
        if len(out) >= _MAX_FINDINGS:
            break
    return out


def _normalize(findings: list[dict]) -> list[dict]:
    """Validate/clamp raw findings to <=5 well-typed {type, content} dicts."""
    clean: list[dict] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        content = f.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        content = content.strip()
        if _is_malformed(content):  # R5: drop structural injection machinery
            continue
        ftype = f.get("type")
        ftype = ftype if ftype in _VALID_TYPES else "note"
        entry = {"type": ftype, "content": content[:500]}
        # R5#2: carry the typed-parse extras through; heuristic findings have
        # none. Field-level (not finding-level) drop here — the typed parse
        # already discarded mismatches, so a bad value can only mean a
        # non-extractor producer, and losing the annotation is the safe floor.
        conf = f.get("confidence")
        if not isinstance(conf, bool) and isinstance(conf, int | float) and 0.0 <= conf <= 1.0:
            entry["confidence"] = round(float(conf), 3)
        ref = f.get("source_ref")
        if (
            isinstance(ref, str)
            and ref.strip()
            and len(ref) <= _MAX_SOURCE_REF_CHARS
            and not _is_malformed(ref)
        ):
            entry["source_ref"] = ref.strip()
        refs = f.get("refs")
        if isinstance(refs, list):
            # Same field-level floor as the annotations above: re-apply the
            # parser's syntax discipline so a non-extractor producer can't
            # smuggle arbitrary strings into the binder.
            entry["refs"] = [
                r
                for r in refs
                if isinstance(r, str)
                and r.strip()
                and len(r) <= _MAX_SOURCE_REF_CHARS
                and not _is_malformed(r)
                and _REF_SYNTAX_RE.match(r)
            ][:_MAX_REFS]
        clean.append(entry)
        if len(clean) >= _MAX_FINDINGS:
            break
    return clean


def _derive_session_refs(transcript_path: str | None) -> dict[str, set[str]] | None:
    """Derive the session ref universe from tool_use records (design D-3).

    Deterministic walk of the transcript JSONL: file-path input keys
    directly; pr/file/spec patterns from command strings. Returns None when
    the transcript is missing or unreadable — the caller degrades to the
    ``no_ref_universe`` status rather than fabricating rejections.
    """
    if not transcript_path:
        return None
    universe: dict[str, set[str]] = {"file": set(), "pr": set(), "spec": set()}
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                content = record.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    inputs = block.get("input")
                    if not isinstance(inputs, dict):
                        continue
                    for key, value in inputs.items():
                        if not isinstance(value, str):
                            continue
                        if key in ("file_path", "path", "notebook_path"):
                            universe["file"].add(value)
                            continue
                        if key != "command":
                            # Codex lane (high): prompts, Write payloads,
                            # descriptions, and queries merely MENTION
                            # artifacts — only executed commands count as
                            # session evidence (design D-3).
                            continue
                        for groups in _UNIVERSE_PR_RE.findall(value):
                            if _first_group(groups):
                                universe["pr"].add(_first_group(groups))
                        for groups in _UNIVERSE_FILE_RE.findall(value):
                            if _first_group(groups):
                                universe["file"].add(_first_group(groups))
                        for match in _UNIVERSE_SPEC_RE.findall(value):
                            universe["spec"].add(match.lower())
    except OSError:
        return None
    return universe


def _normalize_ref_value(kind: str, value: str, cwd: str) -> str:
    """Lexical normalization only (design D-3 rule 2) — no filesystem
    access, so binding is deterministic and side-effect free."""
    value = value.strip().strip("\"'")
    if kind == "file":
        if not os.path.isabs(value):
            value = os.path.join(cwd, value)
        # POSIX-normalize so the tag is platform-stable: on Windows,
        # normpath emits backslashes, which would make the memory tag
        # (and recall queries against it) OS-dependent.
        return Path(os.path.normpath(value)).as_posix()
    if kind == "pr":
        return value.lstrip("#")
    return value.lower()  # spec slug


def _bind_findings(findings: list[dict], transcript_path: str | None, cwd: str) -> None:
    """Design D-3: deterministic per-finding binding, reason-coded.

    Mutates findings in place: sets ``ref_status`` and ``_ref_tags`` (the
    tags ``_stash_findings`` persists). EXACT membership against the
    tool_use-derived universe — no LLM, no fuzzy matching, ever. Statuses:
    ``bound`` / ``unbound_explicit`` (refs ``[]`` or absent) /
    ``unbound_all_rejected`` / ``no_ref_universe`` (transcript unreadable
    or zero tool_use — refs kept as proposed, never claimed rejected).
    """
    universe = _derive_session_refs(transcript_path)
    if universe is not None and not any(universe.values()):
        universe = None  # zero-universe session — same honest degrade
    file_universe: set[str] = set()
    if universe is not None:
        for path in universe["file"]:
            file_universe.add(_normalize_ref_value("file", path, cwd))
    for f in findings:
        tags = ["schema_version:2", f"extractor_prompt_version:{_REFS_PROMPT_VERSION}"]
        refs = f.get("refs") or []
        bound: list[str] = []
        rejected: list[tuple[str, str]] = []
        proposed_unchecked = False
        for ref in refs:
            kind, _, value = ref.partition(":")
            if kind not in _REF_KINDS:
                rejected.append((ref, "bad_kind"))
                continue
            if universe is None:
                proposed_unchecked = True
                tags.append(f"ref_proposed:{ref}")
                continue
            norm = _normalize_ref_value(kind, value, cwd)
            members = file_universe if kind == "file" else universe[kind]
            if norm in members:
                bound.append(f"{kind}:{norm}")
            else:
                rejected.append((ref, "not_in_session"))
        if proposed_unchecked:
            status = "no_ref_universe"
        elif bound:
            status = "bound"
        elif refs:
            status = "unbound_all_rejected"
        else:
            status = "unbound_explicit"
        f["ref_status"] = status
        tags.append(f"ref_status:{status}")
        tags.extend(f"ref_bound:{b}" for b in bound)
        tags.extend(f"ref_rejected:{reason}:{r}" for r, reason in rejected)
        f["_ref_tags"] = tags


def _stash_findings(findings: list[dict], session_id: str, cwd: str) -> int:
    """Write each finding via the PII-gated stash. Returns count written."""
    try:
        from attune.memory.session_stash import (
            SessionStashEntry,
            resolve_backend,
            stash_entry,
        )
    except Exception:  # noqa: BLE001 — attune not importable -> silent no-op
        return 0
    written = 0
    for f in findings:
        try:
            # R5#2: persist the typed-parse annotations as tags — the entry
            # schema stays untouched and recall can filter on them.
            tags: list[str] = []
            if "confidence" in f:
                tags.append(f"confidence:{f['confidence']}")
            if "source_ref" in f:
                tags.append(f"source_ref:{f['source_ref']}")
            # refs v2 (design D-3/D-4): binder output rides the same
            # tag channel — entry schema stays untouched.
            tags.extend(f.get("_ref_tags", []))
            entry = SessionStashEntry.create(
                session_id=session_id, cwd=cwd, type=f["type"], content=f["content"], tags=tags
            )
            if stash_entry(entry):
                written += 1
                # Attach the record id so the chip can offer per-finding
                # review/deletion (short prefix is enough to forget by).
                f["id"] = entry.id
        except Exception:  # noqa: BLE001 — one bad finding must not abort the rest
            continue
    if written:
        try:
            backend = resolve_backend()
            prune = getattr(backend, "prune", None) if backend else None
            if callable(prune):
                prune()
        except Exception:  # noqa: BLE001 — prune is best-effort
            pass
    return written


def _status_fields() -> dict:
    """Caller-scoped backend fields for telemetry (best-effort, never raises).

    Makes degraded routing observable locally (cross-provider-memory-
    transport T4'): which backend answered, over which transport, and the
    stable failure reason when this caller has no usable write path.
    """
    try:
        from attune.memory.session_stash import backend_status

        status = backend_status()
        return {
            "backend": status.get("backend"),
            "transport": status.get("transport"),
            "reason": status.get("reason"),
        }
    except Exception:  # noqa: BLE001 — telemetry enrichment is best-effort
        return {}


def _context_enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_STASH_CONTEXT", "1").strip() not in {
        "0",
        "false",
        "no",
    }


def _emit_additional_context(findings: list[dict], written: int) -> int:
    """Print a compact findings summary as Stop-hook ``additionalContext``.

    Emits the Claude Code >= 2.1.163 envelope
    ``{"hookSpecificOutput": {"hookEventName": "Stop",
    "additionalContext": "..."}}`` on stdout so the just-stashed insights
    surface into the current session's next turn. No-op when nothing was
    written or the feature is disabled; never raises (best-effort).

    Returns the character count of the injected summary (0 when skipped),
    so the caller's telemetry can record the context cost.
    """
    if written <= 0 or not findings or not _context_enabled():
        return 0
    lines = [
        f"\U0001f9e0 Stashed {written} session finding(s) to attune memory "
        "(recall later with /recall):"
    ]
    stashed = [f for f in findings if f.get("id")] or findings[:written]
    for f in stashed:
        content = str(f.get("content", "")).strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:157] + "..."
        short_id = str(f.get("id", ""))[:8]
        id_part = f" `{short_id}`" if short_id else ""
        lines.append(f"- [{f.get('type', 'note')}]{id_part} {content}")
    lines.append(
        "Review: `/recall review` prunes with a checklist; " "`/recall drop <id>` deletes one."
    )
    summary = "\n".join(lines)
    try:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "additionalContext": summary,
                    }
                }
            )
        )
        sys.stdout.flush()
        return len(summary)
    except (OSError, ValueError, TypeError):
        # INTENTIONAL: context injection is best-effort; the disk stash
        # already succeeded, so a stdout failure must not change exit status.
        return 0


def main() -> int:
    """Entry point — acts once per substantive session, never raises."""
    try:
        if not _enabled():
            return 0
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        session_id = payload.get("session_id") or "unknown"
        transcript_path = payload.get("transcript_path")
        cwd = str(payload.get("cwd") or Path.cwd())

        sentinel = _stash_sentinel(session_id)
        if sentinel is not None and sentinel.exists():
            return 0  # already stashed this session

        # Utilization gate: only snapshot once the session has real content.
        try:
            min_util = float(os.environ.get("ATTUNE_MEMORY_STASH_MIN_UTIL", _DEFAULT_MIN_UTIL))
        except ValueError:
            min_util = _DEFAULT_MIN_UTIL
        if estimate_utilization is not None and transcript_path:
            util = estimate_utilization(transcript_path)
            if util < min_util:
                _diag(f"skip session={session_id} util={util:.3f} < gate {min_util}")
                return 0  # too little so far; let a later, fuller stop capture it

        text = _read_transcript_tail(transcript_path)

        # Memory-feedback-signal STEP 2 (MI-1..MI-4): score this session's
        # surfacing records against the tail. Isolated — a scorer failure
        # must never disturb the stash duties below (MI-4), and an empty
        # tail still yields per-item `unscored` verdicts (MI-2).
        try:
            from _memory_verdicts import score_session

            n = score_session(session_id, text)
            if n:
                _diag(f"verdicts session={session_id} scored={n}")
        except Exception:  # noqa: BLE001 — verdict scoring is best-effort
            _diag(f"verdict scoring failed (isolated) session={session_id}")

        if not text.strip():
            return 0

        raw = _extract_via_ollama(text)
        findings = _normalize(raw) if raw else []
        extractor = "ollama"
        if not findings:
            # Ollama unavailable, timed out, or yielded nothing usable —
            # fall back to the heuristic rather than stash nothing.
            findings = _normalize(_extract_heuristic(text))
            extractor = "heuristic"
        if not findings:
            _diag(f"skip session={session_id} extraction yielded no findings")
            return 0

        # refs v2 (flag-gated, design D-3): bind ONLY typed extractor
        # output — heuristic findings are v1-shaped by design. Isolated:
        # a binder failure must never block the stash.
        if extractor == "ollama" and _refs_v2_enabled():
            try:
                _bind_findings(findings, transcript_path, cwd)
            except Exception:  # noqa: BLE001 — binding is best-effort
                _diag(f"ref binding failed (isolated) session={session_id}")

        written = _stash_findings(findings, session_id=session_id, cwd=cwd)
        _diag(
            f"stash session={session_id} findings={len(findings)} written={written}"
            + (" — WRITE PATH FAILED (attune import or backend write)" if written == 0 else "")
        )

        # Mark done AFTER work so a crash mid-extract retries next stop.
        if sentinel is not None:
            try:
                sentinel.parent.mkdir(parents=True, exist_ok=True)
                sentinel.write_text("done\n", encoding="utf-8")
            except OSError:
                # INTENTIONAL: a missing sentinel only means we may re-stash
                # next stop (idempotent enough); never worth failing on.
                pass

        # Surface the stashed findings into the current session's next turn
        # via Stop-hook additionalContext (best-effort; older CC ignores it).
        injected = _emit_additional_context(findings, written)
        log_memory_event(
            "session_stash",
            session_id=session_id,
            findings=len(findings),
            written=written,
            extractor=extractor,
            injected_chars=injected,
            **_status_fields(),
        )
        return 0
    except Exception:  # noqa: BLE001 — a Stop hook must never crash the session
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
