# Contributing

## Development Setup

```bash
uv sync --extra dev
uv tool install --force /Users/jplatta/repos/skillex
```

## Local Workflow

1. Configure the shared skills repo:

```bash
skillex config set-remote <repo-url>
```

2. Initialize the local agent directory you want to work from:

```bash
skillex init claude
skillex init codex
skillex init gemini
```

3. Run tests before committing:

```bash
uv run python -m pytest
```

## Project Conventions

- Use `--agent` explicitly in examples and tests.
- Treat the remote skills repo as the source of truth for shared skills.
- Do not commit repo-local test installs like `.claude/`, `.codex/`, or `.gemini/`.
- Keep commit messages focused and descriptive.

## Pull Requests

- Include a short summary of the change.
- Note any CLI behavior changes.
- Mention test coverage or manual verification performed.
