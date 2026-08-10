"""Tests for the just-in-time recall PreToolUse hook.

The hook is a standalone script; it's loaded via importlib (the
``test_session_memory_hooks.py`` pattern) so the map lookup, the
surface-once sentinel gate, the injection payload, and the fail-safe
control flow can be exercised without a live Claude Code session.

Spec: docs/specs/just-in-time-recall/ (R2-R6).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import time
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]  # fresh load so module-level env reads are clean
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def jit_mod(tmp_path, monkeypatch):
    """Load the hook with the sentinel dir isolated to tmp_path."""
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    monkeypatch.delenv("ATTUNE_JIT_RECALL", raising=False)
    # _state reads the env var at call time, but reload both modules so
    # nothing cached from another test's load leaks in.
    _load_module("_state")
    return _load_module("jit_recall")


def _run(jit_mod, monkeypatch, capsys, payload: dict) -> tuple[int, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = jit_mod.main()
    return rc, capsys.readouterr().out


def _payload(tool: str = "AskUserQuestion", session: str = "sess-1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "session_id": session,
        "tool_input": {"questions": []},
    }


# ==========================================================================
# Map content (R2, R5)
# ==========================================================================


def test_map_has_ask_user_question_proof_entry(jit_mod):
    rules = jit_mod.RECALL_MAP["AskUserQuestion"]
    assert rules, "proof-case entry missing"
    assert rules[0]["rule_id"] == "question-shape"
    assert "(Recommended)" in rules[0]["text"]


def test_map_entries_have_stable_safe_rule_ids(jit_mod):
    for tool, rules in jit_mod.RECALL_MAP.items():
        for rule in rules:
            assert rule["rule_id"] == jit_mod._safe(
                rule["rule_id"], "rule"
            ), f"{tool}: rule_id {rule['rule_id']!r} is not filesystem-safe"
            assert rule["text"].strip(), f"{tool}: empty rule text"


def test_broad_tool_entries_require_content_filter(jit_mod):
    """A rule keyed on a broad tool MUST scope itself via match_substring
    or match_regex, or it fires on the session's first such call (R3)."""
    for tool in ("Bash", "Edit", "Write", "Read"):
        for rule in jit_mod.RECALL_MAP.get(tool, []):
            assert rule.get("match_substring") or rule.get("match_regex"), (
                f"{tool}/{rule['rule_id']}: broad-tool rule without a "
                "content filter would fire on every session's first call"
            )


def test_map_regexes_compile(jit_mod):
    """Every match_regex in the map must be a valid pattern."""
    import re as _re

    for _tool, rules in jit_mod.RECALL_MAP.items():
        for rule in rules:
            pattern = rule.get("match_regex")
            if pattern:
                _re.compile(pattern)  # raises on a bad pattern


# ==========================================================================
# Command-shape regex scoping (#1265)
# ==========================================================================


def _bash_payload(command: str, session: str = "sess-rx") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "session_id": session,
        "tool_input": {"command": command},
    }


def test_zsh_bracket_compare_fires_on_escaped_lt(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload('[ "$a" \\< "$b" ] && echo lt'))
    assert rc == 0
    assert "zsh-bracket-string-compare" not in out  # rule_id never leaks
    assert "condition expected" in out


def test_zsh_bracket_compare_silent_on_plain_test(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload('[ "$a" = "$b" ] && echo eq'))
    assert rc == 0
    assert "condition expected" not in out


def test_zsh_eqword_fires_on_separator(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("echo ===LEAD==="))
    assert rc == 0
    assert "PATH lookup" in out


def test_zsh_eqword_silent_on_flag_assignment(jit_mod, monkeypatch, capsys):
    # --flag=value and a==b comparisons must NOT trip the =word rule.
    rc, out = _run(
        jit_mod, monkeypatch, capsys, _bash_payload('grep --color=auto x; [ "$a" == "$b" ]')
    )
    assert rc == 0
    assert "PATH lookup" not in out


def test_zsh_word_split_fires_on_scalar_for_loop(jit_mod, monkeypatch, capsys):
    # `for w in $LIST` — bash idiom; zsh loops once over the whole string.
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload('SAFE="a b c"; for w in $SAFE; do echo $w; done'),
    )
    assert rc == 0
    assert "word-split" in out


def test_zsh_word_split_fires_on_braced_var(jit_mod, monkeypatch, capsys):
    rc, out = _run(
        jit_mod, monkeypatch, capsys, _bash_payload("for f in ${FILES}; do wc -l $f; done")
    )
    assert rc == 0
    assert "word-split" in out


def test_zsh_word_split_silent_on_safe_shapes(jit_mod, monkeypatch, capsys):
    # Command substitution DOES split in zsh; explicit word lists and
    # array expansions are fine — none of these may trip the rule.
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload(
            "for f in $(ls); do echo $f; done; "
            "for w in a b c; do echo $w; done; "
            'for x in "${arr[@]}"; do echo $x; done'
        ),
    )
    assert rc == 0
    assert "word-split" not in out


def test_zsh_status_readonly_fires_on_assignment(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("status=$(gh pr checks 1)"))
    assert rc == 0
    assert "READ-ONLY" in out


def test_zsh_colon_modifier_fires_on_var_path_concat(jit_mod, monkeypatch, capsys):
    # `$REPO:tests/...` — zsh consumes `:t` as the tail modifier.
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("pytest $REPO:tests/unit"))
    assert rc == 0
    assert "Brace the expansion" in out


def test_zsh_colon_modifier_fires_inside_double_quotes(jit_mod, monkeypatch, capsys):
    # Double quotes do NOT protect — the modifier still applies.
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload('ls "$IMG:latest"'))
    assert rc == 0
    assert "Brace the expansion" in out


def test_zsh_colon_modifier_silent_on_safe_shapes(jit_mod, monkeypatch, capsys):
    # Braced expansion, digit ports, and PATH-style `:/` never trip it.
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("pytest ${REPO}:tests/unit; curl $HOST:8080; PATH=$PATH:/usr/bin"),
    )
    assert rc == 0
    assert "Brace the expansion" not in out


def test_edit_import_rule_fires_once(jit_mod, monkeypatch, capsys):
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "session_id": "sess-ed",
        "tool_input": {"file_path": "x.py", "new_string": "import re\n"},
    }
    rc, out = _run(jit_mod, monkeypatch, capsys, payload)
    assert rc == 0
    assert "SAME edit" in out
    rc2, out2 = _run(jit_mod, monkeypatch, capsys, payload)
    assert rc2 == 0
    assert out2 == ""  # surface-once sentinel


def test_bad_regex_never_blocks(jit_mod, monkeypatch, capsys):
    """A malformed pattern degrades to silent no-op for that rule (R4)."""
    jit_mod.RECALL_MAP["Bash"].append(
        {"rule_id": "bad-regex", "match_regex": "([unclosed", "text": "never shown"}
    )
    try:
        rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("echo hello"))
        assert rc == 0
        assert "never shown" not in out
    finally:
        jit_mod.RECALL_MAP["Bash"].pop()


# ==========================================================================
# Injection payload (R6 proof case)
# ==========================================================================


def test_ask_user_question_surfaces_rule(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _payload())
    assert rc == 0
    envelope = json.loads(out)
    ctx = envelope["hookSpecificOutput"]
    assert ctx["hookEventName"] == "PreToolUse"
    assert "AskUserQuestion" in ctx["additionalContext"]
    assert "(Recommended)" in ctx["additionalContext"]
    assert "ONE question per turn" in ctx["additionalContext"]


def test_unmapped_tool_is_silent_no_op(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _payload(tool="Read"))
    assert rc == 0
    assert out == ""


# ==========================================================================
# match_substring content filter (release-verify entry)
# ==========================================================================


def _bash_payload(command: str, session: str = "sess-1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "session_id": session,
        "tool_input": {"command": command},
    }


def test_release_rule_fires_on_gh_release_create(jit_mod, monkeypatch, capsys):
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "40-char merge SHA" in ctx


def test_release_rule_silent_on_ordinary_bash(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("git status"))
    assert rc == 0
    assert out == ""


def test_non_matching_rule_writes_no_sentinel(jit_mod, monkeypatch, capsys, tmp_path):
    """A filtered-out rule must stay eligible to fire later in the session."""
    _run(jit_mod, monkeypatch, capsys, _bash_payload("git status"))
    base = tmp_path / "sentinels"
    assert not base.exists() or not list(base.iterdir())
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    assert out != ""


# ==========================================================================
# T2.1 slip-points (git-commit / admin-merge / rebase)
# ==========================================================================


def test_git_commit_rule_fires_on_commit(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("git commit -m 'x'"))
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "LANDED" in ctx


def test_admin_merge_rule_fires_on_pr_merge(jit_mod, monkeypatch, capsys):
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh pr merge 952 --admin --squash"),
    )
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "already merged" in ctx


def test_rebase_rule_fires_on_rebase(jit_mod, monkeypatch, capsys):
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("git rebase main"))
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "UNSIGNED" in ctx


def test_t21_rules_silent_on_unrelated_bash(jit_mod, monkeypatch, capsys):
    """None of the T2.1 substrings appear in an ordinary `ls`, so silent."""
    rc, out = _run(jit_mod, monkeypatch, capsys, _bash_payload("ls -la"))
    assert rc == 0
    assert out == ""


def test_all_rule_ids_are_unique(jit_mod):
    """rule_id keys the per-session sentinel — a dup would cross-silence."""
    ids = [r["rule_id"] for rules in jit_mod.RECALL_MAP.values() for r in rules]
    assert len(ids) == len(set(ids)), f"duplicate rule_id in RECALL_MAP: {ids}"


# ==========================================================================
# lesson_ref resolution (lessons-corpus-rag T4)
# ==========================================================================


class _FakeEntry:
    summary = "Tag mechanics — fake title"
    content = "Don't tag before a squash-merge.   Extra   whitespace\ncollapses."


def _install_fake_lessons(monkeypatch, entry):
    """Inject a fake ``attune.lessons`` so the lazy import resolves to it."""
    import types

    fake = types.ModuleType("attune.lessons")

    class LessonsIndex:
        def get(self, ref):
            return entry if ref else None

    fake.LessonsIndex = LessonsIndex
    monkeypatch.setitem(sys.modules, "attune.lessons", fake)


def test_lesson_ref_appends_resolved_excerpt(jit_mod, monkeypatch, capsys):
    _install_fake_lessons(monkeypatch, _FakeEntry())
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "40-char merge SHA" in ctx  # inline one-liner still leads
    assert "Full lesson — Tag mechanics — fake title:" in ctx
    assert "whitespace collapses" in ctx  # body whitespace normalized


def test_lesson_ref_excerpt_is_bounded(jit_mod, monkeypatch, capsys):
    entry = _FakeEntry()
    entry.content = "word " * 1000
    _install_fake_lessons(monkeypatch, entry)
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    lesson_line = next(line for line in ctx.splitlines() if "Full lesson" in line)
    assert lesson_line.endswith("…")
    assert len(lesson_line) < jit_mod._LESSON_EXCERPT_CHARS + 100


def test_lesson_ref_import_failure_falls_back_to_inline(jit_mod, monkeypatch, capsys):
    """Older install / stale checkout: the one-liner must still surface."""
    monkeypatch.setitem(sys.modules, "attune.lessons", None)  # import -> ImportError
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "40-char merge SHA" in ctx
    assert "Full lesson" not in ctx


def test_lesson_ref_unknown_slug_falls_back_to_inline(jit_mod, monkeypatch, capsys):
    _install_fake_lessons(monkeypatch, None)  # get() returns None for any ref
    rc, out = _run(
        jit_mod,
        monkeypatch,
        capsys,
        _bash_payload("gh release create v9.9.9 --target abc123"),
    )
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "40-char merge SHA" in ctx
    assert "Full lesson" not in ctx


def test_all_lesson_refs_resolve_against_real_corpus(jit_mod):
    """Drift guard: slugs derive from lesson TITLES, so a title edit in
    the corpus silently dangles any ``lesson_ref`` pointing at it."""
    lessons = pytest.importorskip("attune.lessons")
    repo_root = Path(__file__).resolve().parents[3]
    idx = lessons.LessonsIndex(lessons.find_lessons_file(repo_root))
    for tool, rules in jit_mod.RECALL_MAP.items():
        for rule in rules:
            ref = rule.get("lesson_ref")
            if not ref:
                continue
            assert idx.get(ref) is not None, (
                f"{tool}/{rule['rule_id']}: lesson_ref {ref!r} does not "
                "resolve — was the lesson's title edited?"
            )


# ==========================================================================
# Surface-once gate (R3, D5)
# ==========================================================================


def test_second_fire_same_session_is_silent(jit_mod, monkeypatch, capsys):
    rc1, out1 = _run(jit_mod, monkeypatch, capsys, _payload())
    rc2, out2 = _run(jit_mod, monkeypatch, capsys, _payload())
    assert (rc1, rc2) == (0, 0)
    assert out1 != ""
    assert out2 == ""


def test_new_session_surfaces_again(jit_mod, monkeypatch, capsys):
    _run(jit_mod, monkeypatch, capsys, _payload(session="sess-1"))
    rc, out = _run(jit_mod, monkeypatch, capsys, _payload(session="sess-2"))
    assert rc == 0
    assert out != ""


def test_sentinel_written_after_emit(jit_mod, monkeypatch, capsys, tmp_path):
    _run(jit_mod, monkeypatch, capsys, _payload())
    sentinels = list((tmp_path / "sentinels").iterdir())
    assert len(sentinels) == 1
    assert sentinels[0].name.startswith(".jit-recalled-sess-1-")


def test_missing_session_id_dedups_via_transcript_stem(jit_mod, monkeypatch, capsys, tmp_path):
    """A payload without session_id but with transcript_path still
    dedups per session — the transcript stem IS the session uuid."""
    payload = _payload()
    del payload["session_id"]
    payload["transcript_path"] = "/tmp/projects/x/abcd-1234.jsonl"
    _, out1 = _run(jit_mod, monkeypatch, capsys, payload)
    _, out2 = _run(jit_mod, monkeypatch, capsys, payload)
    assert out1 != ""
    assert out2 == ""  # suppressed within the same (transcript) session
    names = [p.name for p in (tmp_path / "sentinels").iterdir()]
    assert names and all("abcd-1234" in n for n in names)


def test_no_identity_fails_open_and_writes_no_sentinel(jit_mod, monkeypatch, capsys, tmp_path):
    """No session_id AND no transcript_path: surface every time, write
    NOTHING — never a shared 'unknown' bucket where the first fire
    suppresses the rule machine-wide for the TTL (the 2026-07-13
    headless-collapse regression guard)."""
    payload = _payload()
    del payload["session_id"]
    _, out1 = _run(jit_mod, monkeypatch, capsys, payload)
    _, out2 = _run(jit_mod, monkeypatch, capsys, payload)
    assert out1 != "" and out2 != ""  # fail-open: fires both times
    base = tmp_path / "sentinels"
    leftover = [p.name for p in base.iterdir()] if base.is_dir() else []
    assert leftover == []


def test_prune_removes_only_stale_jit_sentinels(jit_mod, tmp_path):
    base = tmp_path / "sentinels"
    base.mkdir(parents=True, exist_ok=True)
    stale = base / ".jit-recalled-old-rule"
    fresh = base / ".jit-recalled-new-rule"
    other = base / ".compact-warned-x"
    for p in (stale, fresh, other):
        p.write_text("", encoding="utf-8")
    old = time.time() - jit_mod._SENTINEL_TTL_SECONDS - 60
    import os

    os.utime(stale, (old, old))
    os.utime(other, (old, old))
    jit_mod._prune_stale()
    assert not stale.exists()
    assert fresh.exists()
    assert other.exists(), "must not touch other hooks' sentinels"


# ==========================================================================
# Fail-safety + off-switch (R4)
# ==========================================================================


def test_malformed_stdin_exits_zero(jit_mod, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert jit_mod.main() == 0
    assert capsys.readouterr().out == ""


def test_crash_in_lookup_exits_zero(jit_mod, monkeypatch, capsys):
    # A weird RECALL_MAP object makes .get() raise inside main().
    class Boom:
        def get(self, *_a):
            raise RuntimeError("kaboom")

    monkeypatch.setattr(jit_mod, "RECALL_MAP", Boom())
    rc, out = _run(jit_mod, monkeypatch, capsys, _payload())
    assert rc == 0
    assert out == ""


def test_env_off_switch_disables(jit_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_JIT_RECALL", "0")
    rc, out = _run(jit_mod, monkeypatch, capsys, _payload())
    assert rc == 0
    assert out == ""


def test_missing_sentinel_dir_still_surfaces(monkeypatch, capsys, tmp_path):
    """Without a sentinel dir helper the hook surfaces (no gate) and exits 0."""
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "s"))
    mod = _load_module("jit_recall")
    monkeypatch.setattr(mod, "_sentinel_dir", None)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload())))
    assert mod.main() == 0
    assert "additionalContext" in capsys.readouterr().out


# ==========================================================================
# Registration drift guard
# ==========================================================================


def test_hook_registered_for_all_mapped_tools(jit_mod):
    """The hooks.json matcher must cover every tool keyed in RECALL_MAP —
    a map entry whose tool isn't matched never fires (silent dead rule)."""
    hooks = json.loads((_HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    pre = hooks["hooks"]["PreToolUse"]
    jit_entries = [g for g in pre if any("jit_recall.py" in h["command"] for h in g["hooks"])]
    assert jit_entries, "jit_recall.py not registered for PreToolUse"
    matched = set(jit_entries[0]["matcher"].split("|"))
    assert matched == set(jit_mod.RECALL_MAP.keys()), (
        f"hooks.json matcher {matched} != RECALL_MAP tools "
        f"{set(jit_mod.RECALL_MAP.keys())} — update the matcher when "
        "adding a tool to the map"
    )
