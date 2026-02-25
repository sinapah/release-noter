#!/usr/bin/env python3
"""Fetch GitHub release notes for a specific version or version range.

Examples:
  # Single release
  python github_release_notes_cli.py https://github.com/owner/repo/releases 1.2.3

  # Single release, write to folder
  python github_release_notes_cli.py https://github.com/owner/repo/releases v1.2.3 -o ./notes

  # Range (inclusive)
  python github_release_notes_cli.py https://github.com/owner/repo/releases 0.9.0 1.2.3

Some TODOs:
1. Add an optional --verbose mode with status/progress messages.
2. Add unit tests for version parsing and range selection.
3. Add integration tests against a mocked GitHub API response.
4. Add optional GitHub token support to reduce API rate-limit issues.
5. Document and standardize the `uv tool run --from ... github-release-notes` UX.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Release:
    tag_name: str
    name: str
    body: str
    html_url: str
    prerelease: bool
    draft: bool


def parse_repo_from_release_page(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL.

    Accepts URLs such as:
      - https://github.com/owner/repo/releases
      - https://github.com/owner/repo/releases/tag/v1.2.3
      - https://github.com/owner/repo
    """
    parsed = urlparse(url)

    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("URL must point to github.com")

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("Could not parse owner/repo from URL")

    owner, repo = parts[0], parts[1]
    return owner, repo


def github_api_get_json(url: str) -> list[dict]:
    req = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-release-notes-cli",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


def fetch_all_releases(owner: str, repo: str) -> list[Release]:
    releases: list[Release] = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100&page={page}"
        chunk = github_api_get_json(url)

        if not chunk:
            break

        for raw in chunk:
            releases.append(
                Release(
                    tag_name=raw.get("tag_name") or "",
                    name=raw.get("name") or "",
                    body=raw.get("body") or "",
                    html_url=raw.get("html_url") or "",
                    prerelease=bool(raw.get("prerelease")),
                    draft=bool(raw.get("draft")),
                )
            )

        page += 1

    return releases


def normalize_v_prefix(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def find_exact_release(releases: Iterable[Release], version: str) -> Release | None:
    candidates = {version, (f"v{version}" if not version.startswith("v") else version[1:])}

    for rel in releases:
        if rel.prerelease or rel.draft:
            continue
        if rel.tag_name in candidates:
            return rel
    return None


def parse_semver_like(version: str) -> tuple[int, ...] | None:
    """Parse a semver-like version into a numeric tuple.

    Accepts values like 1.2.3, v1.2, 2.0.0+build.
    Rejects pre-release strings (e.g. 1.2.3-rc1).
    """
    v = normalize_v_prefix(version.strip())

    if "-" in v:
        return None

    v = v.split("+", 1)[0]
    if not re.fullmatch(r"\d+(?:\.\d+)*", v):
        return None

    return tuple(int(x) for x in v.split("."))


def pad_tuple(t: tuple[int, ...], length: int) -> tuple[int, ...]:
    if len(t) >= length:
        return t
    return t + (0,) * (length - len(t))


def semver_lte(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    n = max(len(a), len(b))
    return pad_tuple(a, n) <= pad_tuple(b, n)


def semver_in_range(v: tuple[int, ...], start: tuple[int, ...], end: tuple[int, ...]) -> bool:
    return semver_lte(start, v) and semver_lte(v, end)


def select_releases_in_range(releases: Iterable[Release], start: str, end: str) -> list[Release]:
    start_parsed = parse_semver_like(start)
    end_parsed = parse_semver_like(end)
    if start_parsed is None or end_parsed is None:
        raise ValueError("Range bounds must be stable semver-like versions (e.g. 1.2.3)")

    if not semver_lte(start_parsed, end_parsed):
        raise ValueError(f"Invalid range: start '{start}' is greater than end '{end}'")

    selected: list[tuple[tuple[int, ...], Release]] = []

    for rel in releases:
        if rel.prerelease or rel.draft:
            continue

        parsed = parse_semver_like(rel.tag_name)
        if parsed is None:
            continue

        if semver_in_range(parsed, start_parsed, end_parsed):
            selected.append((parsed, rel))

    selected.sort(key=lambda item: item[0])
    return [rel for _, rel in selected]


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def render_release_note(rel: Release) -> str:
    title = rel.name.strip() or rel.tag_name
    return f"# {title}\n\nTag: {rel.tag_name}\nURL: {rel.html_url}\n\n{rel.body.strip()}\n"


def write_outputs(releases: list[Release], output_dir: str | None) -> None:
    if output_dir is None:
        for idx, rel in enumerate(releases):
            if idx > 0:
                print("\n" + "=" * 80 + "\n")
            print(render_release_note(rel))
        return

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for rel in releases:
        filename = safe_filename(rel.tag_name or rel.name or "release") + ".md"
        target = out / filename
        target.write_text(render_release_note(rel), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch GitHub release notes for a specific version or a version range. "
            "Pre-releases are ignored."
        )
    )
    parser.add_argument(
        "release_page_url",
        help="GitHub project release page URL (e.g. https://github.com/owner/repo/releases)",
    )
    parser.add_argument(
        "start_or_version",
        help="Single version (e.g. 1.2.3) or range start version",
    )
    parser.add_argument(
        "end_version",
        nargs="?",
        help="Optional range end version (inclusive)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Folder to write markdown files. If omitted, writes to stdout.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        owner, repo = parse_repo_from_release_page(args.release_page_url)
        releases = fetch_all_releases(owner, repo)

        if args.end_version is None:
            rel = find_exact_release(releases, args.start_or_version)
            if rel is None:
                no_v = normalize_v_prefix(args.start_or_version)
                rel = find_exact_release(releases, no_v)

            if rel is None:
                print(
                    f"Release '{args.start_or_version}' not found for {owner}/{repo} (excluding pre-releases).",
                    file=sys.stderr,
                )
                return 2

            selected = [rel]
        else:
            selected = select_releases_in_range(releases, args.start_or_version, args.end_version)
            if not selected:
                print(
                    (
                        f"No releases found in range [{args.start_or_version}, {args.end_version}] "
                        f"for {owner}/{repo} (excluding pre-releases)."
                    ),
                    file=sys.stderr,
                )
                return 3

        write_outputs(selected, args.output_dir)
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except HTTPError as e:
        print(f"GitHub API HTTP error: {e.code} {e.reason}", file=sys.stderr)
        return 1
    except URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
