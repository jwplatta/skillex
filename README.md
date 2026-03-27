# skillex CLI

## Motivation

I want a bash or python CLI that allows agents from different providers and CLIs to use skills I've created. I want all the skills I have to be in one place so that I only have to edit them in on place and they are easy to access and reuse with different agents.

## Description and Design

to pull and push skills. In general we want to be able to build a skill in, e.g. a project specific repo and the push it to the my skills manager. When we push a new skill, we will need to write a commit message and version the skill. When we pull a new skill, it should pull to the local project folder the agent is using and it should include the skill's version.

We will need to make sure that the agent is configured to use ther user's git account. I'm not entirely sure how to handle this. Either the agent needs to be able to pull and push directly to github, but then it's pulling and pushing a whole repo which we DO NOT want. Rather we want the agent to be pulling and pushing specific skills. So I think the better move is to have the skillex CLI get installed on the host machine and have it pull the git repo to a dotfile like .skillex where it can manage the local state of the skills. Then when skills get installed they'll just get copied from the git repo in this dotfile. And then when the agent needs to pull or push a skill, a change will have to be made in the local skillex repo, commit message written and then the changes will have to pushed. It will need to reject any commits that create merge conflicts.

We should be able to install it with pip:
```sh
$ pip install skillex
```

Basic crud actions on skills:
```sh
$ skillex help
$ skillex list
$ skillex update skill-name
$ skillex push skill-name
$ skillex pull skill-name
$ skillex delete skill-name
```

While the CLI is mostly intended for the agents, we will need a way for the user to initialize the separate coding agents. It should look like:
```sh
$ skillex init codex
$ skillex init claude
$ skillex init gemini
```
This should pull down a the skillex skill to the agent's system/user level directory, e.g. `~/.codex/skills` or `~/.claude/skills` that shows the agent how to use the skillex CLI.

I would like to avoid symlinking in ordert to achieve consistency among the skills because symlinks get broken and I'm moving around all the time. Instead it's okay if skill-A gets installed at version 0.1.0 in codex, then skill-A gets a change pushed up by the Claude agent and increments to like 0.2.0 and codex's install of skill-A falls behind. The codex agent will just need to update it's version of skill-A when it has a chance. After teh version of the skills increments, though, if codex tries to push a change, it should be reject and a help message to should be returned to codex so that it knows to pull the skill before trying to push again. Also, when codex pulls, if it has changes, it should stash those changes some how, and then resolve those changes. If the resolution isn't obvious, codex (the agent) should collaborate with the user to resolve the diff.

## Skill Identity
Each skill should have this sort of json in it that get's used to reflect the skill identity and state:
```json
{
  "name": "market_data",
  "version": "0.2.1",
  "provider": "openai",
  "hash": "...",
  "dependencies": []
}
```

## commit messages

The commit messages should be written by a function provide by the CLI. The agent should just provide the inputs.

```python
def generate_commit_message(
    type: str,
    skill: str,
    version: str,
    summary: str,
    changes: list[str] = None,
    reason: str = None,
    author: str = "agent",
    timestamp: str = None,
) -> str:
```

```python
import re
from datetime import datetime, timezone

ALLOWED_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore"}

def generate_commit_message(type, skill, version, summary,
                            changes=None, reason=None,
                            author="agent", timestamp=None):

    if type not in ALLOWED_TYPES:
        raise ValueError("invalid type")

    if not re.match(r"^[a-z0-9\-]+$", skill):
        raise ValueError("invalid skill name")

    if len(summary) > 80:
        summary = summary[:80]

    timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    header = f"{type}({skill}): v{version} | {summary}"

    parts = [header]

    if changes:
        parts.append("\nCHANGES:")
        parts.extend([f"- {c}" for c in changes])

    if reason:
        parts.append("\nREASON:")
        parts.append(reason)

    parts.append("\nMETA:")
    parts.append(f"author={author}")
    parts.append(f"timestamp={timestamp}")

    return "\n".join(parts)
```

All commits should have one of the following types:
```
feat     # new capability
fix      # bug fix
refactor # no behavior change
docs     # metadata / description only
test     # test changes
chore    # infra / formatting
```

Example commit message:

```
feat(market-data): v0.2.0 | add realtime price endpoint

CHANGES:
- added websocket support
- added symbol validation

REASON:
needed for live trading

META:
author=agent
timestamp=2026-03-27T18:21:00Z
```

## Concerns

You’re underestimating merge complexity. “Reject on conflict” is fine, but agents will constantly hit this. You’ll need:
	•	automatic rebasing for trivial cases
	•	structured diffs (not just raw files) or it gets messy fast
	•	Copying instead of symlinking is safer, but you’re now managing state divergence. That’s fine, but you’ll need:
	•	very explicit version tracking per install
	•	probably a lockfile per agent dir

## References
For claud specifics on skills see: https://code.claude.com/docs/en/skills
For codex specifics on skills see: https://developers.openai.com/codex/skills
For gemini specifics on skills see: https://geminicli.com/docs/cli/skills/