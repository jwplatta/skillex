# Changelog

## Unreleased

## 0.2.0 — 2026-09-21

### Added
- `skillex new <skill-name> --agent <agent>` command scaffolds a new skill directory with a stub `SKILL.md` — no `skill.json` needed
- Auto-heal for partial `skill.json`: if `skill.json` exists but is missing required fields, push now regenerates it automatically (preserving any valid fields) instead of failing
- `--summary` flag on `push` is now optional, defaulting to `"update"`

### Changed
- Removed all emojis from CLI output — all status messages are plain text

### Fixed
- Partial `skill.json` files (missing `hash`, `created`, or `updated`) no longer cause a hard failure on push
- Error messages for invalid `skill.json` now include a recovery tip

## 0.1.0 — 2026-03-27

- Initial release: clone-based central repo setup, agent bootstrap, pull/push/update/remove flows, structured commit message generation, per-agent lockfiles
