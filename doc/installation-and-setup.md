# Installation and Setup

This document covers local installation, first-time setup, and a basic workflow for the `skillex` CLI.

## Prerequisites

- Python 3.10 or newer
- `uv` installed locally
- Git installed locally

## Local Development Install

From the repository root:

```bash
cd /Users/jplatta/repos/skillex
uv sync --extra dev
uv pip install -e .
```

Verify the CLI is available:

```bash
skillex --help
```

If your shell does not pick up the installed command immediately, use:

```bash
uv run skillex --help
```

## Build the Package

To build distributable artifacts locally:

```bash
uv build
```

This creates:

- `dist/skillex-0.1.0.tar.gz`
- `dist/skillex-0.1.0-py3-none-any.whl`

## First-Time Configuration

The first time `skillex` runs, it initializes a central repository at:

```text
~/.skillex
```

This repository stores managed skills under:

```text
~/.skillex/skills/
```

To inspect current config:

```bash
skillex config show
```

To configure a git remote:

```bash
skillex config set-remote <repo-url>
```

Example:

```bash
skillex config set-remote git@github.com:your-user/your-skills-repo.git
```

## Initialize a Provider

Set up one of the supported provider directories:

```bash
skillex init claude
skillex init codex
skillex init gemini
```

Provider skill locations:

- Claude: `~/.claude/skills`
- Codex: `~/.codex/skills`
- Gemini: `~/.gemini/skills`

`skillex init <provider>` will:

- create the provider skills directory if needed
- initialize `~/.skillex` if it does not exist yet
- create and install the `skillex` skill for that provider

## Basic Workflow

List available skills:

```bash
skillex list
```

Install a skill into the current provider:

```bash
skillex pull <skill-name>
```

Update an installed skill:

```bash
skillex update <skill-name>
```

Push changes back to the central repository:

```bash
skillex push <skill-name> \
  --type feat \
  --summary "brief description of the change"
```

Useful push options:

- `--changes "specific change"`
- `--reason "why the change was needed"`
- `--bump patch|minor|major`
- `--provider claude|codex|gemini`

## Migration

To import skills from an existing directory:

```bash
skillex migrate --from /path/to/skills
```

Optional flags:

- `--provider claude`
- `--default-version 0.1.0`

## Testing

Run the current test suite with:

```bash
uv run python -m pytest
```

## Current Limitations

- Remote sync is repository-wide, not scoped to an individual skill.
- Conflict handling is still basic.
- Test coverage exists for core workflow paths, but the CLI is not fully covered yet.
- This is suitable for personal/local use now, but it still needs hardening before broader use.
