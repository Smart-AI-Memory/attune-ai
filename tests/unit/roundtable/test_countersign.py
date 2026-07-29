"""D11c hardened-countersign tests.

Real git repos and worktrees in tmp for the executor end — no
mocked git (the executor→artifact seam is the point). Seat
invocations and the board are injected fakes; the fail-closed
contract (missing/tampered artifacts refuse, tokens only from
verified evidence, different-model rule, R8 never-promotes) is
asserted from the pass record and posted messages.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import pytest

from attune.roundtable.countersign import (
    COUNTERSIGN_TOKEN_RE,
    CountersignError,
    build_countersign_brief,
    format_countersign_token,
    load_receipt_artifact,
    main,
    rerun_receipts_to_artifact,
    run_countersign_pass,
)
from attune.roundtable.rotation import CANONICAL_SEATS


@pytest.fixture
def repo(tmp_path):
    """A tiny real git repo with one committed file."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    (repo / "hello.py").write_text('GREETING = "hello"\n')
    git("add", "hello.py")
    git("commit", "-q", "-m", "seed")
    return repo


PASS_CHECK = ("greet", [sys.executable, "-c", "print('ok')"])
FAIL_CHECK = ("boom", [sys.executable, "-c", "raise SystemExit(3)"])


@pytest.fixture
def artifact(repo, tmp_path):
    """An executor-produced artifact with one pass and one fail."""
    path = tmp_path / "receipts.jsonl"
    rerun_receipts_to_artifact(repo, [PASS_CHECK, FAIL_CHECK], path)
    return path


class FakeBoard:
    """Collects posts; exposes no promote path (R8 by construction)."""

    def __init__(self):
        self.posts = []

    def post_message(self, thread, seat, kind, body, **fields):
        self.posts.append({"thread": thread, "seat": seat, "kind": kind, "body": body, **fields})


def _invoke_countersign(recipe, brief):
    return 0, "VERDICT: COUNTERSIGN\nCITE: greet :: print ok"


def _invoke_dissent(recipe, brief):
    return 0, "VERDICT: DISSENT\nCITE: boom :: exit 3\nREASON: receipt failed"


RECIPES = tuple((seat, (seat, "--stub")) for seat in CANONICAL_SEATS)


# ---------------------------------------------------------------- executor


class TestRerunToArtifact:
    def test_streams_verifiable_artifact(self, repo, tmp_path):
        path = tmp_path / "a.jsonl"
        produced = rerun_receipts_to_artifact(repo, [PASS_CHECK, FAIL_CHECK], path)
        loaded = load_receipt_artifact(path)
        assert [r.label for r in loaded.receipts] == ["greet", "boom"]
        assert loaded.receipts[0].passed and loaded.receipts[0].tail == "ok"
        assert loaded.receipts[1].exit_code == 3
        assert loaded.sha256 == produced.sha256
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert loaded.commit == head

    def test_refuses_existing_path(self, repo, tmp_path):
        path = tmp_path / "a.jsonl"
        path.write_text("occupied")
        with pytest.raises(CountersignError, match="append-only"):
            rerun_receipts_to_artifact(repo, [PASS_CHECK], path)

    def test_refuses_empty_and_capped_checks(self, repo, tmp_path):
        with pytest.raises(CountersignError, match="no receipt"):
            rerun_receipts_to_artifact(repo, [], tmp_path / "a.jsonl")
        many = [(f"c{i}", ["true"]) for i in range(9)]
        with pytest.raises(CountersignError, match="capped"):
            rerun_receipts_to_artifact(repo, many, tmp_path / "b.jsonl")

    def test_refuses_label_breaking_token_grammar(self, repo, tmp_path):
        with pytest.raises(CountersignError, match="label"):
            rerun_receipts_to_artifact(repo, [("a:b", ["true"])], tmp_path / "a.jsonl")

    def test_refuses_bad_ref(self, repo, tmp_path):
        with pytest.raises(CountersignError, match="cannot resolve"):
            rerun_receipts_to_artifact(repo, [PASS_CHECK], tmp_path / "a.jsonl", base_ref="nope")

    def test_scratch_worktree_discarded(self, repo, tmp_path):
        scratch = tmp_path / "scratch"
        rerun_receipts_to_artifact(repo, [PASS_CHECK], tmp_path / "a.jsonl", scratch_root=scratch)
        assert not scratch.exists() or not any(scratch.iterdir())


# ------------------------------------------------------- fail-closed loads


class TestLoadFailsClosed:
    def test_missing_file(self, tmp_path):
        with pytest.raises(CountersignError, match="missing"):
            load_receipt_artifact(tmp_path / "nope.jsonl")

    def test_symlink_refused(self, artifact, tmp_path):
        link = tmp_path / "link.jsonl"
        link.symlink_to(artifact)
        with pytest.raises(CountersignError, match="symlink"):
            load_receipt_artifact(link)

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        with pytest.raises(CountersignError, match="empty"):
            load_receipt_artifact(path)

    def test_garbage_line(self, artifact):
        artifact.write_text(artifact.read_text() + "not json\n")
        with pytest.raises(CountersignError, match="unparseable"):
            load_receipt_artifact(artifact)

    def test_missing_header(self, artifact):
        lines = artifact.read_text().splitlines()
        artifact.write_text("\n".join(lines[1:]) + "\n")
        with pytest.raises(CountersignError, match="header|chain"):
            load_receipt_artifact(artifact)

    def test_naive_tail_tamper_breaks_entry_digest(self, artifact):
        lines = artifact.read_text().splitlines()
        entry = json.loads(lines[1])
        entry["tail"] = "doctored"
        lines[1] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        artifact.write_text("\n".join(lines) + "\n")
        with pytest.raises(CountersignError, match="digest mismatch"):
            load_receipt_artifact(artifact)

    def test_recomputed_digest_tamper_breaks_chain_or_tail_hash(self, artifact):
        # A sophisticated tamper on the LAST entry recomputes the entry
        # digest; the stale tail_sha256 still betrays it.
        lines = artifact.read_text().splitlines()
        entry = json.loads(lines[-1])
        entry["tail"] = "doctored"
        del entry["entry_digest"]
        digest = hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        entry["entry_digest"] = digest
        lines[-1] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        artifact.write_text("\n".join(lines) + "\n")
        with pytest.raises(CountersignError, match="tail digest"):
            load_receipt_artifact(artifact)

    def test_dropped_entry_breaks_chain(self, artifact):
        lines = artifact.read_text().splitlines()
        artifact.write_text("\n".join([lines[0], lines[2]]) + "\n")
        with pytest.raises(CountersignError, match="chain|sequence"):
            load_receipt_artifact(artifact)

    def test_header_only_refused(self, artifact):
        lines = artifact.read_text().splitlines()
        artifact.write_text(lines[0] + "\n")
        with pytest.raises(CountersignError, match="no receipt"):
            load_receipt_artifact(artifact)


# ---------------------------------------------------------------- tokens


class TestToken:
    def test_round_trips_grammar(self):
        token = format_countersign_token("countersign", "codex", "greet", "a" * 64)
        m = COUNTERSIGN_TOKEN_RE.fullmatch(token)
        assert m and m.group("seat") == "codex" and m.group("digest") == "a" * 16

    def test_bad_pieces_refused(self):
        with pytest.raises(CountersignError):
            format_countersign_token("countersign", "codex", "has:colon", "a" * 64)
        with pytest.raises(CountersignError):
            format_countersign_token("countersign", "codex", "greet", "short")


# ---------------------------------------------------------------- passes


class TestCountersignPass:
    def test_countersign_emits_citable_token(self, artifact):
        board = FakeBoard()
        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=board,
            invoke_seat=_invoke_countersign,
            seat_recipes=RECIPES,
        )
        assert record.outcome == "countersigned"
        assert record.token and COUNTERSIGN_TOKEN_RE.fullmatch(record.token)
        assert record.artifact_sha256[:16] in record.token
        assert record.skeptic != "claude"

    def test_dissent_emits_dissent_token(self, artifact):
        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=FakeBoard(),
            invoke_seat=_invoke_dissent,
            seat_recipes=RECIPES,
        )
        assert record.outcome == "dissented"
        assert record.token.startswith("dissent: ")

    def test_invented_cite_is_malformed_no_token(self, artifact):
        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=FakeBoard(),
            invoke_seat=lambda r, b: (0, "VERDICT: COUNTERSIGN\nCITE: invented :: x"),
            seat_recipes=RECIPES,
        )
        assert record.outcome == "malformed-verdict"
        assert record.token is None

    def test_uncited_countersign_is_malformed(self, artifact):
        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=FakeBoard(),
            invoke_seat=lambda r, b: (0, "VERDICT: COUNTERSIGN"),
            seat_recipes=RECIPES,
        )
        assert record.outcome == "malformed-verdict"
        assert record.token is None

    def test_missing_artifact_refuses_without_invoking(self, tmp_path):
        calls = []

        def invoke(recipe, brief):
            calls.append(recipe)
            return 0, "VERDICT: COUNTERSIGN\nCITE: greet :: x"

        record = run_countersign_pass(
            tmp_path / "nope.jsonl",
            lead="claude",
            board=FakeBoard(),
            invoke_seat=invoke,
            seat_recipes=RECIPES,
        )
        assert record.outcome == "no-artifact"
        assert record.token is None and not calls

    def test_tampered_artifact_refuses_without_invoking(self, artifact):
        artifact.write_text(artifact.read_text() + "junk\n")
        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=FakeBoard(),
            invoke_seat=lambda r, b: (0, "VERDICT: COUNTERSIGN\nCITE: greet :: x"),
            seat_recipes=RECIPES,
        )
        assert record.outcome == "bad-artifact"
        assert record.token is None

    def test_lead_never_invoked_as_skeptic(self, artifact):
        seats = []

        def invoke(recipe, brief):
            seats.append(recipe[0])
            return 1, ""  # everyone absent — walk the whole rotation

        record = run_countersign_pass(
            artifact,
            lead="codex",
            board=FakeBoard(),
            invoke_seat=invoke,
            seat_recipes=RECIPES,
        )
        assert "codex" not in seats
        assert record.outcome == "skeptic-absent"
        assert record.token is None

    def test_absent_first_seat_falls_back_once(self, artifact):
        seats = []

        def invoke(recipe, brief):
            seats.append(recipe[0])
            if len(seats) == 1:
                return 1, "unreachable"
            return 0, "VERDICT: COUNTERSIGN\nCITE: greet :: x"

        record = run_countersign_pass(
            artifact,
            lead="claude",
            board=FakeBoard(),
            invoke_seat=invoke,
            seat_recipes=RECIPES,
        )
        assert record.outcome == "countersigned"
        assert record.skeptic == seats[1] != "claude"

    def test_unknown_lead_raises(self, artifact):
        with pytest.raises(CountersignError, match="unknown lead"):
            run_countersign_pass(artifact, lead="gpt", seat_recipes=RECIPES)

    def test_brief_is_built_from_artifact_only(self, artifact):
        loaded = load_receipt_artifact(artifact)
        brief = build_countersign_brief("claude", loaded)
        assert loaded.sha256 in brief
        assert "### greet: PASS" in brief and "### boom: FAIL (exit 3)" in brief

    def test_synthesis_posted_for_chair(self, artifact):
        board = FakeBoard()
        run_countersign_pass(
            artifact,
            lead="claude",
            board=board,
            invoke_seat=_invoke_countersign,
            seat_recipes=RECIPES,
        )
        synth = [p for p in board.posts if p["kind"] == "synthesis"]
        assert synth and "never flips a status (R8)" in synth[0]["body"]


# ------------------------------------------------------------------- CLI


class TestCli:
    def test_rerun_then_verify(self, repo, tmp_path, capsys):
        path = tmp_path / "a.jsonl"
        code = main(
            [
                "rerun",
                str(path),
                "--repo",
                str(repo),
                "--check",
                f"greet :: {sys.executable} -c \"print('ok')\"",
            ]
        )
        assert code == 0
        assert "sha256:" in capsys.readouterr().out
        assert main(["verify", str(path)]) == 0
        path.write_text(path.read_text() + "junk\n")
        assert main(["verify", str(path)]) == 2

    def test_rerun_bad_check_spec(self, repo, tmp_path):
        assert (
            main(["rerun", str(tmp_path / "a.jsonl"), "--repo", str(repo), "--check", "nolabel"])
            == 2
        )

    def test_rerun_refuses_existing_artifact(self, repo, tmp_path):
        path = tmp_path / "a.jsonl"
        path.write_text("occupied")
        assert main(["rerun", str(path), "--repo", str(repo), "--check", "c :: true"]) == 2


# ------------------------------------------------- patch-coverage closure


def _synthetic_artifact(tmp_path, receipt_overrides: dict, *, version=None):
    """A chain-valid two-entry artifact whose receipt entry is tampered
    at the PAYLOAD level (digests recomputed), isolating the per-entry
    validation branches from the chain checks that run first."""
    from attune.roundtable.countersign import _ARTIFACT_VERSION, _entry_digest

    header = {
        "kind": "header",
        "seq": 0,
        "version": version or _ARTIFACT_VERSION,
        "commit": "c" * 40,
    }
    tail = "ok"
    receipt = {
        "kind": "receipt",
        "seq": 1,
        "label": "greet",
        "argv": ["true"],
        "exit_code": 0,
        "tail": tail,
        "tail_sha256": hashlib.sha256(tail.encode()).hexdigest(),
    }
    receipt.update(receipt_overrides)
    path = tmp_path / "synthetic.jsonl"
    prev = ""
    with path.open("w") as handle:
        for entry in (header, receipt):
            entry["prev_digest"] = prev
            entry["entry_digest"] = _entry_digest(entry)
            handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
            prev = str(entry["entry_digest"])
    return path


class TestLoadFailsClosedBranches:
    def test_json_array_line_is_not_an_object(self, artifact):
        artifact.write_text(artifact.read_text() + "[1,2]\n")
        with pytest.raises(CountersignError, match="is not an object"):
            load_receipt_artifact(artifact)

    def test_unsupported_version_refused(self, tmp_path):
        path = _synthetic_artifact(tmp_path, {}, version="v999")
        with pytest.raises(CountersignError, match="unsupported artifact version"):
            load_receipt_artifact(path)

    def test_wrong_kind_is_bad_sequence(self, tmp_path):
        path = _synthetic_artifact(tmp_path, {"kind": "note"})
        with pytest.raises(CountersignError, match="bad sequence"):
            load_receipt_artifact(path)

    def test_non_string_tail_is_malformed(self, tmp_path):
        path = _synthetic_artifact(tmp_path, {"tail": 5})
        with pytest.raises(CountersignError, match="malformed receipt entry"):
            load_receipt_artifact(path)

    def test_non_string_argv_is_malformed(self, tmp_path):
        path = _synthetic_artifact(tmp_path, {"argv": ["true", 3]})
        with pytest.raises(CountersignError, match="malformed argv"):
            load_receipt_artifact(path)


class TestExecutorWorktreeFailure:
    def test_unwritable_scratch_root_raises_runtime_error(self, repo, tmp_path):
        ro_root = tmp_path / "ro"
        ro_root.mkdir()
        ro_root.chmod(0o555)
        try:
            with pytest.raises(RuntimeError, match="worktree add failed"):
                rerun_receipts_to_artifact(
                    repo, [PASS_CHECK], tmp_path / "a.jsonl", scratch_root=ro_root
                )
        finally:
            ro_root.chmod(0o755)


class TestBoardlessPost:
    def test_pass_without_board_prints_instead_of_posting(self, artifact, capsys):
        record = run_countersign_pass(
            artifact,
            CANONICAL_SEATS[0],
            board=None,
            invoke_seat=_invoke_countersign,
            seat_recipes=RECIPES,
        )
        out = capsys.readouterr().out
        assert record.outcome
        assert "countersign" in out.lower() or "[" in out  # printed, not posted


class TestCliRerunUnparseableCommand:
    def test_unclosed_quote_returns_2(self, repo, tmp_path, capsys):
        code = main(
            ["rerun", str(tmp_path / "a.jsonl"), "--repo", str(repo), "--check", 'c :: echo "open']
        )
        assert code == 2
        assert "unparseable command" in capsys.readouterr().out


class TestCliPassCommand:
    def test_pass_success_prints_outcome_and_token(self, artifact, monkeypatch, capsys):
        import attune.roundtable.board as board_mod
        import attune.roundtable.countersign as cs

        class _Record:
            outcome = "countersigned"
            token = "COUNTERSIGN codex greet abc123"

        monkeypatch.setattr(board_mod, "Board", FakeBoard)
        monkeypatch.setattr(cs, "run_countersign_pass", lambda *a, **k: _Record())
        lead = sorted(CANONICAL_SEATS)[0]
        assert main(["pass", str(artifact), "--lead", lead]) == 0
        out = capsys.readouterr().out
        assert "outcome=countersigned" in out
        assert "ledger token:" in out

    def test_pass_without_token_skips_ledger_line(self, artifact, monkeypatch, capsys):
        import attune.roundtable.board as board_mod
        import attune.roundtable.countersign as cs

        class _Record:
            outcome = "dissent"
            token = ""

        monkeypatch.setattr(board_mod, "Board", FakeBoard)
        monkeypatch.setattr(cs, "run_countersign_pass", lambda *a, **k: _Record())
        lead = sorted(CANONICAL_SEATS)[0]
        assert main(["pass", str(artifact), "--lead", lead]) == 0
        out = capsys.readouterr().out
        assert "outcome=dissent" in out
        assert "ledger token:" not in out

    def test_pass_countersign_error_returns_2(self, artifact, monkeypatch, capsys):
        import attune.roundtable.board as board_mod
        import attune.roundtable.countersign as cs

        def _raise(*a, **k):
            raise CountersignError("no seats answered")

        monkeypatch.setattr(board_mod, "Board", FakeBoard)
        monkeypatch.setattr(cs, "run_countersign_pass", _raise)
        lead = sorted(CANONICAL_SEATS)[0]
        assert main(["pass", str(artifact), "--lead", lead]) == 2
        assert "no seats answered" in capsys.readouterr().out
