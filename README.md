# release-noter

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
release-noter --help
```

## Run with `uv tool run` (no local install)

If you want to run directly from Git without installing into your environment:

```bash
uv tool run --from git+https://github.com/sinapah/release_noter release-noter --help
```

For generating notes:

```bash
uv tool run --from git+https://github.com/sinapah/release_noter release-noter https://github.com/OWNER/REPO/releases 1.2.3
```

## Usage

### Single release

```bash
release-noter https://github.com/OWNER/REPO/releases 1.2.3
```

If an exact match is not found, the tool also tries with/without the `v` prefix
and can match stable semver suffixes in prefixed tags such as `mimir-1.2.3`.

### Version range (inclusive)

```bash
release-noter https://github.com/OWNER/REPO/releases 0.9.0 1.2.3
```

Range mode also supports repositories whose release tags include a prefix, such
as `mimir-2.13.0`.

### Write output to folder

```bash
release-noter https://github.com/OWNER/REPO/releases 1.2.3 -o ./notes
```

If `-o/--output-dir` is omitted, output is written to stdout.

## Notes

- The URL can be a project URL or releases URL (for example `https://github.com/prometheus/prometheus` or `https://github.com/prometheus/prometheus/releases`).
- Range bounds must be stable semver-like versions (e.g. `1.2.3`).
- GitHub API rate limits may apply for unauthenticated requests.
