"""Check the Harness onboarding links on a specific Smart AI Memory preview."""

from __future__ import annotations

import argparse
import hashlib
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
        self.anchors: set[str] = set()
        self.assets: set[str] = set()
        self.tag = None
        self.href = None
        self.parts: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if anchor := attributes.get("id"):
            self.anchors.add(anchor)
        if tag == "script" and (source := attributes.get("src")):
            self.assets.add(source)
        if (
            tag == "link"
            and attributes.get("rel") == "stylesheet"
            and (href := attributes.get("href"))
        ):
            self.assets.add(href)
        if tag in {"a", "h1", "h2"}:
            self.tag = tag
            self.href = attributes.get("href")
            self.parts = []

    def handle_data(self, data):
        if self.tag:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != self.tag:
            return
        label = " ".join("".join(self.parts).split())
        if tag in {"h1", "h2"}:
            self.headings.add(label)
        elif self.href:
            self.links.append((label.removesuffix("↗").rstrip(), self.href))
        self.tag = None


def check_journey(
    origin: str, help_receipt: dict, training_receipt: dict, version: str, token: str = ""
):
    if help_receipt["source_commit"] != training_receipt["source_commit"]:
        raise RuntimeError("Help and training receipts name different Harness commits")
    if training_receipt["course"] != "reporting":
        raise RuntimeError("Expected the maintained reporting course receipt")
    headers = "Cache-Control: no-cache\n"
    if token:
        if "\r" in token or "\n" in token:
            raise RuntimeError("Invalid VERCEL_OIDC_TOKEN")
        headers += f"x-vercel-trusted-oidc-idp-token: {token}\n"

    def get(url: str, redirect_to: str | None = None) -> bytes:
        route = urlsplit(url).path
        # Inspect redirects explicitly. Headers travel on stdin so the token
        # stays out of arguments and diagnostics.
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
            input=headers.encode("utf-8"),
            capture_output=True,
            timeout=20,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"{route}: {detail}")
        body, _, response = result.stdout.rpartition(b"\n")
        status, _, redirect = response.decode("utf-8").partition(" ")
        if status in {"401", "403"} or urlsplit(redirect).hostname == "vercel.com":
            raise RuntimeError(
                f"{route}: preview access denied. Use an authorized VERCEL_OIDC_TOKEN."
            )
        if redirect_to is not None:
            if status != "307" or urljoin(url, redirect) != origin + redirect_to:
                raise RuntimeError(f"{route}: expected a temporary redirect to {redirect_to}")
        elif status != "200":
            raise RuntimeError(f"{route}: expected HTTP 200, got {status}")
        return body

    def linked(page: Page, url: str, label: str, path: str) -> str:
        targets = {urljoin(url, href) for name, href in page.links if name == label}
        if targets != {origin + path}:
            raise RuntimeError(f"{urlsplit(url).path}: expected {label!r} to link to {path}")
        return targets.pop()

    def follow(page: Page, url: str, label: str, path: str) -> tuple[Page, str]:
        target = linked(page, url, label, path)
        return Page(get(target).decode("utf-8")), target

    def require_heading(page: Page, url: str, heading: str):
        if heading not in page.headings:
            raise RuntimeError(f"{urlsplit(url).path}: missing heading {heading!r}")

    def check_training_file(name: str, route: str) -> bytes:
        content = get(origin + route)
        if hashlib.sha256(content).hexdigest() != training_receipt["files"][name]:
            raise RuntimeError(f"{route}: bytes differ from the committed training export")
        return content

    homepage_url = origin + "/"
    homepage = Page(get(homepage_url).decode("utf-8"))
    help_page, help_url = follow(
        homepage, homepage_url, "Get started with Harness", "/harness/help/get-started/"
    )
    require_heading(help_page, help_url, "Get started with Harness")
    course_name = training_receipt["course"]
    course = f"/harness/learn/{course_name}"
    practice_anchor = "set-up-the-practice-folder"
    practice_path = f"/harness/help/get-started/#{practice_anchor}"
    get(origin + "/harness/learn/", redirect_to=practice_path)
    if practice_anchor not in help_page.anchors:
        raise RuntimeError(f"{urlsplit(help_url).path}: missing practice setup anchor")
    zip_path = "assets/reporting-practice.zip"
    linked(help_page, help_url, "Download practice ZIP", f"{course}/{zip_path}")
    check_training_file(f"{course_name}/{zip_path}", f"{course}/{zip_path}")
    compatibility_path = "assets/compatibility.json"
    linked(help_page, help_url, "tested versions and results", f"{course}/{compatibility_path}")
    check_training_file(f"{course_name}/{compatibility_path}", f"{course}/{compatibility_path}")
    linked(help_page, help_url, "Continue to the reporting course", f"{course}/")
    overview_url = linked(help_page, help_url, "Browse the six Harness tutorials", f"{course}/")
    overview = Page(check_training_file(f"{course_name}/index.html", f"{course}/").decode("utf-8"))
    require_heading(overview, overview_url, "Harness in practice")
    require_heading(overview, overview_url, "Course tutorials")
    linked(overview, overview_url, "Set up the practice folder", practice_path)
    linked(overview, overview_url, "Help Center", "/harness/help/")
    docs_url = origin + "/docs/"
    docs = Page(get(docs_url).decode("utf-8"))
    linked(docs, docs_url, "Browse the reporting tutorials", f"{course}/")
    linked(docs, docs_url, "Set up the practice folder", practice_path)
    lesson_title = "Build your first report"
    lesson_path = f"{course}/02-build/"
    lesson_url = linked(overview, overview_url, lesson_title, lesson_path)
    lesson = Page(
        check_training_file(f"{course_name}/02-build/index.html", lesson_path).decode("utf-8")
    )
    for asset in ("assets/app.js", "assets/styles.css"):
        name = f"{course_name}/{asset}"
        route = f"{course}/{asset}?v={training_receipt['files'][name][:12]}"
        if origin + route not in {urljoin(lesson_url, url) for url in lesson.assets}:
            raise RuntimeError(f"{lesson_path}: missing current version of {asset}")
        check_training_file(name, route)
    if json.loads(get(urljoin(lesson_url, "lesson.json")))["title"] != lesson_title:
        raise RuntimeError(f"{urlsplit(lesson_url).path}lesson.json: unexpected lesson title")
    reading, reading_url = follow(
        lesson, lesson_url, "Read full lesson", f"{course}/02-build/read.html"
    )
    require_heading(reading, reading_url, lesson_title)
    linked(reading, reading_url, "Help Center", "/harness/help/")
    return_help, return_help_url = follow(lesson, lesson_url, "Help Center", "/harness/help/")
    require_heading(return_help, return_help_url, "Harness Help Center")
    linked(return_help, return_help_url, "Get started with Harness", "/harness/help/get-started/")

    for route, expected in (
        ("/harness-help-static/import.json", help_receipt),
        ("/harness/learn/import.json", training_receipt),
    ):
        if json.loads(get(origin + route)) != expected:
            raise RuntimeError(f"{route}: does not match the committed export receipt")
    build = get(origin + "/harness/help/build.json")
    metadata = json.loads(build)
    if (
        hashlib.sha256(build).hexdigest() != help_receipt["build_sha256"]
        or metadata["status"] != "published"
        or metadata["published_version"] != version
    ):
        raise RuntimeError("Served Help build metadata differs from the committed export")

    setup_path = f"{course}/setup.html"
    setup_url = origin + setup_path
    setup_html = check_training_file(f"{course_name}/setup.html", setup_path).decode("utf-8")
    setup = Page(setup_html)
    if "select-a-practice-runtime" not in setup.anchors:
        raise RuntimeError(f"{setup_path}: missing original setup anchor")
    linked(setup, setup_url, "Set up the practice folder", practice_path)
    if "uv venv" in setup_html or "uv pip install" in setup_html:
        raise RuntimeError(f"{setup_path}: duplicate practice setup commands")
    check_training_file("archive/index.html", "/harness/learn/archive/")
    legacy_course = "1.7.0-preparation"
    for file, route in (
        ("setup.html", "setup.html"),
        ("02-build/index.html", "02-build/"),
        ("02-build/read.html", "02-build/read.html"),
        ("assets/current-checks.json", "assets/current-checks.json"),
        ("assets/reporting-example.zip", "assets/reporting-example.zip"),
    ):
        check_training_file(f"{legacy_course}/{file}", f"/harness/learn/{legacy_course}/{route}")
    print("Passed: homepage → Get Started → course overview → lesson 2 → reading view")
    print("Verified Docs discovery, the return to Help, the Learn redirect, and historical routes")
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
    version = exported("help", "build.json")["published_version"]
    check_journey(
        origin, help_receipt, training_receipt, version, os.environ.get("VERCEL_OIDC_TOKEN", "")
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None
