"""Project a pinned canonical walkthrough snapshot; --check detects drift."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content/harness-help"
SNAPSHOT = CONTENT / "tutorials-1.3.0.source.md"
MANIFEST = CONTENT / "walkthrough-provenance.json"
OUTPUT = CONTENT / "walkthroughs.generated.json"
RELEASE = "0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0"
SOURCE_PATH = "docs/tutorials-1.3.0.md"
RELEASE_DOCS = f"https://github.com/Smart-AI-Memory/attune-harness/blob/{RELEASE}/docs/"


def project(source: str) -> dict[str, str]:
    """Keep canonical instructions, setup, results and limits together."""
    sections = dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", source, re.M | re.S))
    mapping = {
        "start-and-continue": "Navigation: an accepted intent",
        "plan-and-accept": "Specification workflow: preview and acceptance",
        "research": "Four workflows: research a question",
        "save-and-resume": "Session continuity: saved answers in another session",
    }
    result = {}
    for slug, heading in mapping.items():
        text = sections[heading].strip()
        # Only presentation changes: the action table becomes a numbered list.
        text = re.sub(r"^\| (\d+) \| (.*?) \|$", r"\1. \2", text, flags=re.M)
        text = re.sub(r"^\| (Step|---).*\n?", "", text, flags=re.M)
        text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)
        text = re.sub(r"^Title: (.*)$", r"## \1", text, flags=re.M)
        if slug in {"start-and-continue", "save-and-resume"}:
            text = (
                "## Before you begin\n\n"
                "Use the selected environment from [Get started](/harness/help/get-started/). "
                "For a disposable example, [prepare the trainer fixture](#prepare-a-disposable-form-example) "
                "before following the numbered actions. Set `TASK` to its actual canonical "
                "saved-task directory. In a POSIX shell, for the example path below, use "
                "`TASK='/absolute/path/to/training-form/saved-task'`; replace the parent path "
                "with the unused absolute directory you chose for the fixture. For real "
                "work, use your existing task's canonical directory instead.\n\n" + text
            )
            text += (
                "\n\n## Prepare a disposable form example\n\n"
                + sections["Trainer setup for the two form walkthroughs"].strip()
            )
        if slug in {"plan-and-accept", "research"}:
            text = (
                "Use the isolated environment and release example checkout from "
                "[Get started](/harness/help/get-started/). `R` names that checkout.\n\n" + text
            )
        text += (
            "\n\n## Verification scope\n\n" + sections["Verification and release boundary"].strip()
        )
        text = (
            "**Reference note:** The release-pinned local workflow guide retains older "
            "optional-extra installation instructions and describes forms intake as future work. "
            "Those statements conflict with the 1.3.0 package metadata and released GUI. "
            "Use [Get started](/harness/help/get-started/) and "
            "[Dependencies and reference](/harness/help/dependencies/) for 1.3.0 setup. "
            "Treat that older guide as an input-limit/design reference.\n\n" + text
        )
        # Relative guide links refer to the release, not unpublished main docs.
        text = re.sub(
            r"\]\((cli-guide|local-workflow|memory-saving)\.md([^)]*)\)",
            lambda m: f"]({RELEASE_DOCS}{m[1]}.md{m[2]})",
            text,
        )
        result[slug] = text + "\n"
    return result


def main() -> None:
    """Update only from a committed upstream source, or verify local projection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--commit")
    args = parser.parse_args()
    if args.repo or args.commit:
        if (
            args.check
            or not args.repo
            or not args.commit
            or not re.fullmatch(r"[0-9a-f]{40}", args.commit)
        ):
            parser.error("updates require --repo and a full --commit; do not combine with --check")
        repo = args.repo.resolve(strict=True)
        source = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{args.commit}:{SOURCE_PATH}"], encoding="utf-8"
        )
        if RELEASE not in source:
            parser.error("the source must retain its 1.3.0 release boundary")
        SNAPSHOT.write_text(source, encoding="utf-8")
        MANIFEST.write_text(
            json.dumps(
                {
                    "source_repository": "Smart-AI-Memory/attune-harness",
                    "source_path": SOURCE_PATH,
                    "source_commit": args.commit,
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "source_publication": "local reviewed tutorial branch; unpublished",
                    "behavior_version": "1.3.0",
                    "behavior_commit": RELEASE,
                    "maintenance": "Update upstream canonical instructions; refresh this snapshot and regenerate. Do not edit the snapshot or generated JSON.",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    source = SNAPSHOT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(source.encode()).hexdigest() != manifest["source_sha256"]:
        raise SystemExit(
            "canonical snapshot hash changed: refresh from its committed upstream source"
        )
    expected = json.dumps(project(source), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("walkthrough projection drift: regenerate from the unchanged snapshot")
        print("Four walkthrough projections and canonical source hash match.")
    else:
        OUTPUT.write_text(expected, encoding="utf-8")


if __name__ == "__main__":
    main()
