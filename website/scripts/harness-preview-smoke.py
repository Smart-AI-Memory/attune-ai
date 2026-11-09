"""Check the Harness onboarding links on a specific Smart AI Memory preview."""

import argparse
import json
import os
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[2]
GITHUB = "repos/Smart-AI-Memory/attune-ai/deployments"
VERCEL_BOT = "vercel[bot]"
PREVIEW_ENV = "Preview – smartaimemory.com"
PREVIEW_ORIGIN = re.compile(
    r"https://smartaimemory-[a-z0-9]{9}-[a-z0-9]+(?:-[a-z0-9]+)*\.vercel\.app/?"
)


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=20).strip()


def deployment_origin(commit: str) -> str:
    deployments = json.loads(command("gh", "api", "--method", "GET", f"{GITHUB}?sha={commit}"))
    candidates = [
        item
        for item in deployments
        if item["sha"] == commit
        and item["environment"] == PREVIEW_ENV
        and item["production_environment"] is False
        and item["creator"]["login"] == VERCEL_BOT
    ]
    if not candidates:
        raise RuntimeError(f"No Smart AI Memory preview deployment for {commit}")
    deployment = max(candidates, key=lambda item: item["id"])
    statuses = json.loads(
        command("gh", "api", "--method", "GET", f"{GITHUB}/{deployment['id']}/statuses")
    )
    if (
        not statuses
        or statuses[0]["state"] != "success"
        or statuses[0]["creator"]["login"] != VERCEL_BOT
    ):
        raise RuntimeError(
            f"Smart AI Memory preview for {commit} has no current successful deployment status"
        )
    # The exact-commit Vercel deployment record identifies the project and team.
    origin = statuses[0]["environment_url"]
    if not PREVIEW_ORIGIN.fullmatch(origin):
        raise RuntimeError("Expected an immutable Smart AI Memory Vercel preview URL")
    return origin.rstrip("/")


class Page(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.headings: set[str] = set()
        self.tag = None
        self.href = None
        self.parts: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "h1"}:
            self.tag = tag
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.tag:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != self.tag:
            return
        label = " ".join("".join(self.parts).split())
        if tag == "h1":
            self.headings.add(label)
        elif self.href:
            self.links.append((label.removesuffix("↗").rstrip(), self.href))
        self.tag = None


def check_journey(
    origin: str, help_receipt: dict, training_receipt: dict, version: str, token: str = ""
):
    headers = "Cache-Control: no-cache\n"
    if token:
        if "\r" in token or "\n" in token:
            raise RuntimeError("Invalid VERCEL_OIDC_TOKEN")
        headers += f"x-vercel-trusted-oidc-idp-token: {token}\n"

    def get(url: str) -> str:
        route = urlsplit(url).path
        # Ignore user curl configuration and avoid redirects. Headers travel
        # on stdin so the token stays out of arguments and diagnostics.
        result = subprocess.run(
            [
                "curl",
                "--disable",
                "--silent",
                "--show-error",
                "--max-time",
                "15",
                "--header",
                "@-",
                "--write-out",
                "\n%{http_code} %{redirect_url}",
                "--url",
                url,
            ],
            input=headers,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        if result.returncode:
            raise RuntimeError(f"{route}: {result.stderr.strip()}")
        body, _, response = result.stdout.rpartition("\n")
        status, _, redirect = response.partition(" ")
        if status in {"401", "403"} or urlsplit(redirect).hostname == "vercel.com":
            raise RuntimeError(
                f"{route}: preview access denied. Use an authorized VERCEL_OIDC_TOKEN."
            )
        if status != "200":
            raise RuntimeError(f"{route}: expected HTTP 200, got {status}")
        return body

    def follow(page: Page, url: str, label: str, path: str) -> tuple[Page, str]:
        targets = {urljoin(url, href) for name, href in page.links if name == label}
        if targets != {origin + path}:
            raise RuntimeError(f"{urlsplit(url).path}: expected {label!r} to link to {path}")
        target = targets.pop()
        return Page(get(target)), target

    def require_heading(page: Page, url: str, heading: str):
        if heading not in page.headings:
            raise RuntimeError(f"{urlsplit(url).path}: missing heading {heading!r}")

    homepage_url = origin + "/"
    homepage = Page(get(homepage_url))
    help_page, help_url = follow(
        homepage, homepage_url, "Get started with Harness", "/harness/help/get-started/"
    )
    require_heading(help_page, help_url, f"Get started with Harness {version}")
    course = "/harness/learn/" + training_receipt["course"]
    setup, setup_url = follow(
        help_page, help_url, "Get ready for the course", f"{course}/setup.html"
    )
    require_heading(setup, setup_url, "Get ready for the course")
    lesson_title = "Build your first report"
    lesson, lesson_url = follow(
        setup, setup_url, f"Continue to {lesson_title}", f"{course}/02-build/"
    )
    if json.loads(get(urljoin(lesson_url, "lesson.json")))["title"] != lesson_title:
        raise RuntimeError(f"{urlsplit(lesson_url).path}lesson.json: unexpected lesson title")
    reading, reading_url = follow(
        lesson, lesson_url, "Read full lesson", f"{course}/02-build/read.html"
    )
    require_heading(reading, reading_url, lesson_title)

    for route, expected in (
        ("/harness-help-static/import.json", help_receipt),
        ("/harness/learn/import.json", training_receipt),
    ):
        if json.loads(get(origin + route)) != expected:
            raise RuntimeError(f"{route}: does not match the committed export receipt")
    print("Passed: homepage → Help → course setup → lesson 2 → reading view")
    print(f"Both preview receipts match Harness {help_receipt['source_commit']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD", help="Website commit to verify (default: HEAD)")
    args = parser.parse_args()
    commit = command(
        "git", "rev-parse", "--verify", "--end-of-options", f"{args.commit}^{{commit}}"
    )
    origin = deployment_origin(commit)
    print(f"Checking {commit} at {origin}", flush=True)

    def exported(directory: str, filename: str) -> dict:
        return json.loads(
            command("git", "show", f"{commit}:website/public/harness-{directory}-static/{filename}")
        )

    help_receipt = exported("help", "import.json")
    training_receipt = exported("training", "import.json")
    if help_receipt["source_commit"] != training_receipt["source_commit"]:
        raise RuntimeError("Committed Help and training receipts name different Harness commits")
    version = exported("help", "build.json")["published_version"]
    check_journey(
        origin, help_receipt, training_receipt, version, os.environ.get("VERCEL_OIDC_TOKEN", "")
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None
