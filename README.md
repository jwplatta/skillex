# skillex

`skillex` is a Python CLI for managing reusable AI agent skills from a shared git repository.

It clones a central skills repo into `~/.skillex`, installs copied skill directories into agent-specific folders like `.claude/skills` or `.codex/skills`, and tracks installed versions with a per-agent `.skillex.lock` file.

## Current Status

The project is usable for personal/local workflows now.

Implemented:

- clone-based central repo setup with `skillex config set-remote <url>`
- agent bootstrap with `skillex init claude|codex|gemini`
- pull/install/update/remove-from-repo/push/delete flows
- structured commit message generation
- per-agent lockfiles for installed skills
- support for repo-local test agent dirs like `.claude/skills` and `.codex/skills`

Still basic:

- conflict handling
- richer merge workflows
- broader CLI test coverage

## Install

For host-machine use with `uv`:

```bash
uv tool install --force /Users/jplatta/repos/skillex
```

Then run:

```bash
skillex --help
```

For development:

```bash
uv sync --extra dev
uv run python -m pytest
```

## Core Workflow

1. Configure the shared skills repository:

```bash
skillex config set-remote https://github.com/jwplatta/agent-skills
```

2. Initialize an agent directory:

```bash
skillex init claude
skillex init codex
skillex init gemini
```

3. Pull a skill for a specific agent:

```bash
skillex pull skillex --agent claude
skillex pull skillex --agent codex
```

4. Push a changed skill back to the shared repo:

```bash
skillex push skillex \
  --agent claude \
  --type docs \
  --summary "update shared skillex instructions" \
  --changes "rewrote the skill to be agent-neutral" \
  --reason "the remote skillex skill should work for all agents"
```

## Commands

```bash
skillex list
skillex init <claude|codex|gemini>
skillex pull <skill-name> --agent <claude|codex|gemini>
skillex update <skill-name> --agent <claude|codex|gemini>
skillex remove <skill-name>
skillex push <skill-name> --agent <claude|codex|gemini> --type <type> --summary "<summary>"
skillex delete <skill-name>
skillex config show
skillex config get-remote
skillex config set-remote <repo-url>
```

## Commit Message Format

Pushes generate structured commit messages with:

- a typed header
- an optional `CHANGES` section
- an optional `REASON` section
- a required `META` section

Supported types:

- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`

## Lockfiles

Each agent skills directory gets its own `.skillex.lock`, for example:

- `.claude/skills/.skillex.lock`
- `.codex/skills/.skillex.lock`

The lockfile records:

- installed version
- installed hash
- install timestamp
- source path in `~/.skillex`

## Documentation

- Setup guide: [doc/installation-and-setup.md](doc/installation-and-setup.md)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT. See [LICENSE](LICENSE).
