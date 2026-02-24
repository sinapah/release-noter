# GitHub Release Notes CLI

A small Python CLI to fetch GitHub release notes for:

- a single release version, or
- a version range (inclusive)

Pre-releases and draft releases are ignored.

## Requirements

- Python 3.10+
- Internet access to call the GitHub API

## Install with pip

From this project directory:

```bash
pip install .
```

For editable/development install:

```bash
pip install -e .
```

After installation, the command is available as:

```bash
github-release-notes --help
```

## Usage

### Single release

```bash
github-release-notes https://github.com/OWNER/REPO/releases 1.2.3
```

If an exact match is not found, the tool also tries with/without the `v` prefix (for example `1.2.3` and `v1.2.3`).

### Version range (inclusive)

```bash
github-release-notes https://github.com/OWNER/REPO/releases 0.9.0 1.2.3
```

### Write output to folder

```bash
github-release-notes https://github.com/OWNER/REPO/releases 1.2.3 -o ./notes
```

If `-o/--output-dir` is omitted, output is written to stdout.

## Notes

- The URL can be a project URL or releases URL (for example `https://github.com/OWNER/REPO` or `https://github.com/OWNER/REPO/releases`).
- Range bounds must be stable semver-like versions (e.g. `1.2.3`).
- GitHub API rate limits may apply for unauthenticated requests.
