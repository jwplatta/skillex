from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import git
from click.testing import CliRunner

from skillex import cli as cli_module
from skillex.cli import cli
from skillex.core.install import InstallManager
from skillex.core.lockfile import LockfileManager
from skillex.core.repository import SkillexRepository
from skillex.models import Skill
from skillex.providers.codex import CodexProvider
from skillex.utils.commit import generate_commit_message


def create_local_repo_clone(repo_path: Path) -> SkillexRepository:
    repo_path.mkdir(parents=True)
    raw_repo = git.Repo.init(repo_path)
    (repo_path / "README.md").write_text("test repo\n")
    raw_repo.index.add(["README.md"])
    raw_repo.index.commit("init")

    repo = SkillexRepository(repo_path)
    repo.initialize()
    return repo


def create_skill(path: Path, name: str = "demo-skill", version: str = "0.1.0") -> Skill:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("# Demo\n")
    (path / "skill.json").write_text(json.dumps({
        "name": name,
        "version": version,
        "hash": "placeholder",
        "dependencies": [],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "author": "test",
        "description": "demo skill",
    }))

    skill = Skill(path)
    skill.metadata.hash = skill.compute_hash()
    skill.save_metadata()
    return skill


def test_generate_commit_message_includes_structured_sections() -> None:
    message = generate_commit_message(
        type="feat",
        skill="demo-skill",
        version="0.2.0",
        summary="add demo flow",
        changes=["added install path", "updated metadata"],
        reason="needed for smoke testing",
        author="tester",
        timestamp="2026-03-27T18:21:00Z",
    )

    assert message.startswith("feat(demo-skill): v0.2.0 | add demo flow")
    assert "CHANGES:" in message
    assert "- added install path" in message
    assert "REASON:" in message
    assert "author=tester" in message
    assert "timestamp=2026-03-27T18:21:00Z" in message


def test_install_manager_updates_lockfile(tmp_path: Path) -> None:
    repo = create_local_repo_clone(tmp_path / ".skillex")

    skill = create_skill(repo.skills_path / "demo-skill")
    installer = InstallManager(repo)

    success, error = installer.install_skill("demo-skill", "claude", tmp_path / "agent")

    assert success is True
    assert error is None
    assert (tmp_path / "agent" / "demo-skill" / "SKILL.md").exists()

    lockfile = LockfileManager(tmp_path / "agent")
    entry = lockfile.get_entry("demo-skill")
    assert entry is not None
    assert entry.version == skill.metadata.version
    assert entry.hash == skill.metadata.hash


def test_fresh_install_copies_skill_and_creates_lock_entry(tmp_path: Path) -> None:
    repo = create_local_repo_clone(tmp_path / ".skillex")
    source_skill = create_skill(repo.skills_path / "fresh-install-skill", name="fresh-install-skill")
    installer = InstallManager(repo)
    agent_dir = tmp_path / "empty-agent"

    success, error = installer.install_skill("fresh-install-skill", "codex", agent_dir)

    assert success is True
    assert error is None
    assert (agent_dir / "fresh-install-skill" / "SKILL.md").exists()
    assert (agent_dir / "fresh-install-skill" / "skill.json").exists()

    installed_skill = Skill(agent_dir / "fresh-install-skill")
    lockfile = LockfileManager(agent_dir)
    entry = lockfile.get_entry("fresh-install-skill")

    assert installed_skill.metadata.version == source_skill.metadata.version
    assert installed_skill.metadata.hash == source_skill.metadata.hash
    assert entry is not None
    assert entry.version == source_skill.metadata.version
    assert entry.hash == source_skill.metadata.hash


def test_lockfile_rebuilds_when_corrupted(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    skill = create_skill(agent_dir / "demo-skill")
    lockfile_path = agent_dir / ".skillex.lock"
    lockfile_path.write_text("{not valid json")

    manager = LockfileManager(agent_dir)
    lock = manager.load()

    assert "demo-skill" in lock.skills
    assert lock.skills["demo-skill"].version == skill.metadata.version
    assert lock.skills["demo-skill"].source == "recovered-from-installed-skill"


def test_lockfile_rebuilds_when_missing_installed_skill_entries(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    create_skill(agent_dir / "demo-skill")
    create_skill(agent_dir / "second-skill", name="second-skill")

    lockfile_path = agent_dir / ".skillex.lock"
    lockfile_path.write_text(json.dumps({
        "version": "1.0",
        "updated": datetime.now().isoformat(),
        "skills": {
            "demo-skill": {
                "version": "0.1.0",
                "hash": "sha256:stale",
                "installed": datetime.now().isoformat(),
                "source": "/tmp/source",
            }
        },
    }))

    manager = LockfileManager(agent_dir)
    lock = manager.load()

    assert set(lock.skills.keys()) == {"demo-skill", "second-skill"}
    assert lock.skills["second-skill"].source == "recovered-from-installed-skill"


def test_repository_push_without_remote_returns_explicit_error(tmp_path: Path) -> None:
    repo = create_local_repo_clone(tmp_path / ".skillex")
    create_skill(repo.skills_path / "demo-skill")

    success, error = repo.push("demo-skill", "feat(demo-skill): v0.1.1 | add demo")

    assert success is False
    assert error is not None
    assert "No remote configured" in error


def test_cli_push_without_remote_does_not_bump_installed_skill(
    tmp_path: Path, monkeypatch
) -> None:
    repo = create_local_repo_clone(tmp_path / ".skillex")

    provider_dir = tmp_path / "provider-skills"
    skill = create_skill(provider_dir / "demo-skill")

    class FakeProvider:
        def get_skills_directory(self) -> Path:
            return provider_dir

    monkeypatch.setattr(cli_module, "_repo", repo)
    monkeypatch.setattr(cli_module, "detect_current_provider", lambda: "claude")
    monkeypatch.setattr(cli_module, "get_provider", lambda name: FakeProvider())
    monkeypatch.setattr(cli_module, "check_for_updates_quietly", lambda: None)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "push",
            "demo-skill",
            "--type",
            "feat",
            "--summary",
            "add demo flow",
        ],
    )

    reloaded_skill = Skill(provider_dir / "demo-skill")

    assert result.exit_code == 0
    assert "Push failed: No remote configured" in result.output
    assert reloaded_skill.metadata.version == skill.metadata.version
    assert not (repo.skills_path / "demo-skill").exists()


def test_cli_push_creates_skill_json_for_new_skill_without_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    repo = create_local_repo_clone(tmp_path / ".skillex")

    provider_dir = tmp_path / "provider-skills"
    skill_dir = provider_dir / "brand-new-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Brand New\n")

    class FakeProvider:
        def get_skills_directory(self) -> Path:
            return provider_dir

    monkeypatch.setattr(cli_module, "_repo", repo)
    monkeypatch.setattr(cli_module, "detect_current_provider", lambda: "claude")
    monkeypatch.setattr(cli_module, "get_provider", lambda name: FakeProvider())
    monkeypatch.setattr(cli_module, "check_for_updates_quietly", lambda: None)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "push",
            "brand-new-skill",
            "--type",
            "docs",
            "--summary",
            "seed new skill",
        ],
    )

    created_skill = Skill(skill_dir)

    assert result.exit_code == 0
    assert "Creating metadata for new skill" in result.output
    assert created_skill.metadata.name == "brand-new-skill"
    assert created_skill.metadata.version == "0.1.0"
    assert created_skill.metadata.hash.startswith("sha256:")
    assert not (repo.skills_path / "brand-new-skill").exists()


def test_provider_materializes_bootstrap_skill_from_skill_directory(tmp_path: Path) -> None:
    provider = CodexProvider()
    destination = tmp_path / "skillex"

    provider.materialize_skillex_skill(destination)

    skill_md = (destination / "SKILL.md").read_text()
    commands_ref = (destination / "references" / "commands.md").read_text()

    assert "provider:" not in "\n".join(skill_md.splitlines()[:6])
    assert "shared repository" in skill_md
    assert "--agent codex" in skill_md
    assert "skillex init codex" in commands_ref


def test_repository_clones_remote_when_url_provided(tmp_path: Path) -> None:
    remote_repo_path = tmp_path / "remote"
    remote_repo_path.mkdir()
    remote_repo = git.Repo.init(remote_repo_path)
    (remote_repo_path / "README.md").write_text("remote repo\n")
    remote_repo.index.add(["README.md"])
    remote_repo.index.commit("init remote")

    clone_path = tmp_path / "clone"
    repo = SkillexRepository(clone_path)
    repo.initialize(remote_url=str(remote_repo_path))

    assert repo.repo is not None
    assert repo.repo_path == clone_path.resolve()
    assert repo.skills_path.exists()
    assert repo.repo.remote("origin").url.endswith(str(remote_repo_path))
