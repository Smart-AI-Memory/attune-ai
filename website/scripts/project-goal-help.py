"""Validate and project the authored goal guide and its release metadata."""

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[1]
CONTENT = WEBSITE / "content" / "harness-help"


class GuideCheck(HTMLParser):
    """Reject executable markup and broken local bindings in the static source."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.targets: list[str] = []
        self.main_goals = 0
        self.testing_goals = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "iframe", "form"}:
            raise ValueError(f"Executable or submitting element: {tag}")
        for key, value in attrs:
            if key.startswith("on") or (value and value.strip().lower().startswith("javascript:")):
                raise ValueError(f"Executable attribute: {key}")
        identity = attributes.get("id")
        if identity:
            if identity in self.ids:
                raise ValueError(f"Duplicate ID: {identity}")
            self.ids.add(identity)
        if tag == "details":
            classes = (attributes.get("class") or "").split()
            self.main_goals += "goal-item" in classes
            self.testing_goals += "testing-goal" in classes
        for key in ("data-copy", "data-status"):
            if attributes.get(key):
                self.targets.append(attributes[key])
        href = attributes.get("href") or ""
        if href.startswith("#"):
            self.targets.append(href[1:])
        for key in ("href", "src"):
            path = (attributes.get(key) or "").split("#")[0]
            if path.startswith("/harness-help-assets/"):
                resolved = (WEBSITE / "public" / path.lstrip("/")).resolve()
                if (
                    not resolved.is_relative_to(WEBSITE / "public" / "harness-help-assets")
                    or not resolved.is_file()
                ):
                    raise ValueError(f"Unavailable asset: {path}")


def main() -> None:
    """Validate the master and write, or verify, its deterministic projection."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    html = (CONTENT / "goal-guide.source.html").read_text(encoding="utf-8")
    release = json.loads((CONTENT / "release.json").read_text(encoding="utf-8"))
    notice = (
        "Released guidance."
        if release["status"] == "published"
        else f"Preparation only; this version is not yet released. Use published {release['published_version']} until publication."
    )
    for key, value in {
        "HARNESS_VERSION": release["version"],
        "HARNESS_SOURCE_REF": release["source_ref"],
        "RELEASE_SLUG": release["slug"],
        "RELEASE_NOTICE": notice,
    }.items():
        html = html.replace("{{" + key + "}}", value)
    check = GuideCheck()
    check.feed(html)
    missing = set(check.targets) - check.ids
    if missing:
        raise ValueError(f"Missing local targets: {sorted(missing)}")
    if (check.main_goals, check.testing_goals) != (21, 6):
        raise ValueError("Expected 21 main goals and six testing FAQs")
    payload = {
        "html": html,
        "data": json.loads((CONTENT / "goal-guide.data.json").read_text(encoding="utf-8")),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    destination = CONTENT / "goal-guide.generated.json"
    if args.check:
        if destination.read_text(encoding="utf-8") != rendered:
            raise ValueError("Goal help projection drift; run scripts/project-goal-help.py")
    else:
        destination.write_text(rendered, encoding="utf-8")
    print(
        "Goal help projection valid: 21 main goals, six testing FAQs, all local bindings/assets available."
    )


if __name__ == "__main__":
    main()
