"""Command-line interface for skillex.

Provides commands for managing AI agent skills across multiple providers.
"""

import click
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import shutil
import tempfile

from .core.repository import SkillexRepository
from .core.install import InstallManager
from .core.version import VersionManager
from .utils.commit import generate_commit_message, validate_skill_name
from .providers import get_provider, detect_current_provider, list_providers
from .models import SkillMetadata, Skill


# Global repository instance (initialized on first use)
_repo: Optional[SkillexRepository] = None


def get_repo() -> SkillexRepository:
    """Get or initialize the global repository instance."""
    global _repo
    if _repo is None:
        _repo = SkillexRepository()
        try:
            _repo.initialize()
        except ValueError as exc:
            raise click.ClickException(str(exc))
    return _repo


def resolve_agent(agent: Optional[str], provider: Optional[str]) -> Optional[str]:
    """Resolve the explicit or detected agent/provider value."""
    selected = agent or provider
    if selected:
        return selected.lower()
    return detect_current_provider()


def bootstrap_local_skill(skill_path: Path, agent: str, author: str = "system") -> Skill:
    """Create the local bootstrap skillex skill outside the central repository."""
    provider_obj = get_provider(agent)
    if not provider_obj:
        raise click.ClickException(f"Unknown agent: {agent}")

    provider_obj.materialize_skillex_skill(skill_path)
    skill_json_path = skill_path / "skill.json"

    skill_json = {
        "name": "skillex",
        "version": "0.1.0",
        "hash": "placeholder",
        "dependencies": [],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "author": author,
        "description": "Skillex CLI usage instructions",
    }

    with open(skill_json_path, "w") as f:
        json.dump(skill_json, f, indent=2)

    skill = Skill(skill_path)
    skill.metadata.hash = skill.compute_hash()
    skill.save_metadata()
    return skill


def initialize_missing_skill_metadata(
    skill_path: Path,
    skill_name: str,
    bump: str,
    author: str = "agent",
) -> Skill:
    """Create a minimal skill.json for a brand-new local skill directory."""
    initial_version = "1.0.0" if bump == "major" else "0.1.0"
    skill_json_path = skill_path / "skill.json"

    skill_json = {
        "name": skill_name,
        "version": initial_version,
        "hash": "placeholder",
        "dependencies": [],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "author": author,
        "description": f"{skill_name} skill",
    }

    with open(skill_json_path, "w") as f:
        json.dump(skill_json, f, indent=2)

    skill = Skill(skill_path)
    skill.metadata.hash = skill.compute_hash()
    skill.save_metadata()
    return skill


def check_for_updates_quietly() -> None:
    """Check for updates from remote without blocking.

    This is called before most commands to ensure local is up-to-date.
    """
    try:
        repo = get_repo()
        has_updates, _ = repo.check_for_updates()

        if has_updates:
            click.secho(
                "💡 Tip: Updates available. Run 'skillex pull' to sync.",
                fg="yellow",
                dim=True
            )
    except Exception:
        # Silently ignore errors in background check
        pass


@click.group()
@click.version_option(version="0.1.0", prog_name="skillex")
def cli():
    """Skillex - Manage AI agent skills across multiple providers.

    Skillex maintains a central git repository at ~/.skillex and copies
    skills to provider-specific directories (e.g., ~/.claude/skills).

    Common workflow:
      1. skillex init claude           # Set up Claude provider
      2. skillex pull python-testing   # Install a skill
      3. Make changes to skill...
      4. skillex push python-testing   # Push changes back

    Use 'skillex COMMAND --help' for more information on a command.
    """
    pass


@cli.command()
def help():
    """Show this help message."""
    ctx = click.get_current_context()
    click.echo(ctx.parent.get_help())


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(list_providers(), case_sensitive=False),
    help="Filter by provider (claude, codex, gemini)"
)
def list(provider):
    """List all skills in the repository.

    \b
    Examples:
      skillex list                 # List all skills
      skillex list --provider claude  # List only Claude skills
    """
    check_for_updates_quietly()

    repo = get_repo()
    skills = repo.get_all_skills()

    if not skills:
        click.echo("No skills found in repository.")
        click.echo("\nTip: Use 'skillex migrate' to import existing skills")
        return

    # Display skills
    click.secho("\nAvailable Skills:", bold=True)
    click.echo()

    for skill in sorted(skills, key=lambda s: s.metadata.name):
        name = skill.metadata.name
        version = skill.metadata.version
        desc = skill.metadata.description

        click.echo(f"  {click.style(name, fg='cyan', bold=True)} v{version}")
        if desc:
            click.echo(f"    {desc}")
        click.echo()


@cli.command()
@click.argument("provider", type=click.Choice(list_providers(), case_sensitive=False))
def init(provider):
    """Initialize a provider with the skillex skill.

    Sets up the provider's skills directory and installs the skillex skill
    that explains how to use the CLI.

    \b
    Examples:
      skillex init claude
      skillex init codex
      skillex init gemini
    """
    provider = provider.lower()
    provider_obj = get_provider(provider)

    if not provider_obj:
        click.secho(f"❌ Unknown provider: {provider}", fg="red")
        return

    click.echo(f"Initializing {provider}...")

    # Initialize provider directory
    skills_dir = provider_obj.initialize()
    click.echo(f"✓ Created skills directory: {skills_dir}")

    repo = get_repo()
    click.echo(f"✓ Using repository: {repo.repo_path}")

    repo_skill = repo.get_skill("skillex")
    if repo_skill:
        installer = InstallManager(repo)
        success, error = installer.install_skill("skillex", provider, skills_dir)
    else:
        local_skill_path = skills_dir / "skillex"
        click.echo("Bootstrapping local skillex skill...")
        bootstrap_local_skill(local_skill_path, provider)
        success, error = True, None

    if success:
        click.secho(f"\n✅ Successfully initialized {provider}!", fg="green", bold=True)
        click.echo(f"\nSkillex skill installed at: {skills_dir / 'skillex'}")
        click.echo("\nNext steps:")
        click.echo("  1. Check available skills: skillex list")
        click.echo("  2. Push the bootstrap skill: skillex push skillex --agent " + provider)
        click.echo("  3. Install another skill: skillex pull <skill-name> --agent " + provider)
    else:
        click.secho(f"❌ Failed to install skillex skill: {error}", fg="red")


@cli.command()
@click.argument("skill_name", required=False)
@click.option(
    "--agent",
    type=click.Choice(list_providers(), case_sensitive=False),
    help="Agent to pull for (claude, codex, gemini)"
)
@click.option(
    "--provider",
    hidden=True,
    help="Deprecated alias for --agent"
)
def pull(skill_name, agent, provider):
    """Pull skill(s) from repository to provider directory.

    If no skill name provided, pulls updates for all installed skills.

    \b
    Examples:
      skillex pull python-testing     # Pull specific skill
      skillex pull                   # Pull updates for all installed skills
      skillex pull --provider claude  # Specify provider explicitly
    """
    repo = get_repo()

    # Pull from remote first
    click.echo("Syncing with remote repository...")
    success, error = repo.pull()

    if not success:
        click.secho(f"⚠️  Pull from remote failed: {error}", fg="yellow")
        click.echo("Continuing with local repository...")

    # Detect or use specified provider
    agent = resolve_agent(agent, provider)

    if not agent:
        click.secho(
            "❌ Could not detect agent. Use --agent flag or set SKILLEX_PROVIDER env var",
            fg="red"
        )
        return

    provider_obj = get_provider(agent)
    if not provider_obj:
        click.secho(f"❌ Unknown agent: {agent}", fg="red")
        return

    skills_dir = provider_obj.get_skills_directory()
    installer = InstallManager(repo)

    if skill_name:
        # Pull specific skill
        click.echo(f"Installing {skill_name} to {agent}...")

        success, error = installer.install_skill(skill_name, agent, skills_dir)

        if success:
            click.secho(f"✅ Successfully installed {skill_name}", fg="green")
        else:
            click.secho(f"❌ Failed: {error}", fg="red")
    else:
        # Pull updates for all installed skills
        click.echo(f"Checking for updates in {agent}...")

        updates = installer.check_updates(skills_dir)

        if not updates:
            click.echo("All skills are up-to-date")
            return

        click.echo(f"\nUpdates available for {len(updates)} skill(s):\n")

        for name, installed, latest in updates:
            click.echo(f"  {name}: {installed} -> {latest}")

        if click.confirm("\nUpdate all skills?"):
            for name, _, _ in updates:
                success, error = installer.update_skill(name, skills_dir)
                if success:
                    click.secho(f"✓ Updated {name}", fg="green")
                else:
                    click.secho(f"✗ Failed to update {name}: {error}", fg="red")


@cli.command()
@click.argument("skill_name")
@click.option("--type", "commit_type", required=True,
              type=click.Choice(["feat", "fix", "refactor", "docs", "test", "chore"]),
              help="Type of change")
@click.option("--summary", required=True, help="Brief summary of changes (max 80 chars)")
@click.option("--changes", help="Optional change details to include in the commit message")
@click.option("--reason", help="Reason for the changes")
@click.option("--bump", type=click.Choice(["major", "minor", "patch"]),
              default="patch", help="Version bump type (default: patch)")
@click.option(
    "--agent",
    type=click.Choice(list_providers(), case_sensitive=False),
    help="Agent context (claude, codex, gemini)"
)
@click.option("--provider", hidden=True, help="Deprecated alias for --agent")
def push(skill_name, commit_type, summary, changes, reason, bump, agent, provider):
    """Push skill changes from provider directory to repository.

    Creates a structured commit and pushes to the remote repository.

    \b
    Examples:
      skillex push python-testing \\
        --type feat \\
        --summary "add coverage reporting" \\
        --changes "added pytest-cov" \\
        --reason "needed for CI"
    """
    check_for_updates_quietly()

    # Validate skill name
    if not validate_skill_name(skill_name):
        click.secho(f"❌ Invalid skill name: {skill_name}", fg="red")
        click.echo("Skill names must be lowercase, alphanumeric, and may contain hyphens")
        return

    # Detect provider
    agent = resolve_agent(agent, provider)

    if not agent:
        click.secho("❌ Could not detect agent. Use --agent flag", fg="red")
        return

    provider_obj = get_provider(agent)
    if not provider_obj:
        click.secho(f"❌ Unknown agent: {agent}", fg="red")
        return

    skills_dir = provider_obj.get_skills_directory()
    skill_path = skills_dir / skill_name

    if not skill_path.exists():
        click.secho(f"❌ Skill not found in {agent} directory: {skill_path}", fg="red")
        return

    repo = get_repo()

    # Check if behind remote
    if repo.is_behind_remote():
        click.secho("❌ Local repository is behind remote. Pull first:", fg="red")
        click.echo("  skillex pull")
        return

    try:
        is_new_skill = not (skill_path / "skill.json").exists()
        if is_new_skill:
            click.echo("No skill.json found. Creating metadata for new skill...")
            provider_skill = initialize_missing_skill_metadata(skill_path, skill_name, bump)
            current_version = provider_skill.metadata.version
            new_version = current_version
        else:
            # Load skill from provider directory
            provider_skill = Skill(skill_path)
            current_version = provider_skill.metadata.version
            new_version = VersionManager.bump(current_version, bump)

        # Load skill from provider directory
        if is_new_skill:
            click.echo(f"Version: new skill -> {new_version}")
        else:
            click.echo(f"Version: {current_version} -> {new_version}")

        repo_skill_path = repo.skills_path / skill_name
        had_existing_repo_skill = repo_skill_path.exists()

        with tempfile.TemporaryDirectory(prefix=f"skillex-{skill_name}-") as temp_dir:
            staged_skill_path = Path(temp_dir) / skill_name
            provider_skill.copy_to(staged_skill_path)

            staged_skill = Skill(staged_skill_path)
            staged_skill.metadata.version = new_version
            staged_skill.metadata.hash = staged_skill.compute_hash()
            staged_skill.save_metadata()

            backup_path: Optional[Path] = None
            if had_existing_repo_skill:
                backup_path = Path(temp_dir) / f"{skill_name}-repo-backup"
                shutil.copytree(repo_skill_path, backup_path)

            staged_skill.copy_to(repo_skill_path)

            # Generate commit message
            commit_msg = generate_commit_message(
                type=commit_type,
                skill=skill_name,
                version=new_version,
                summary=summary,
                changes=[changes] if changes else None,
                reason=reason
            )

            click.echo(f"\nCommit message:\n{commit_msg}\n")

            # Push to repository
            click.echo("Pushing to repository...")
            success, error = repo.push(skill_name, commit_msg)

            if not success:
                if had_existing_repo_skill and backup_path is not None:
                    shutil.rmtree(repo_skill_path)
                    shutil.copytree(backup_path, repo_skill_path)
                elif repo_skill_path.exists():
                    shutil.rmtree(repo_skill_path)

                click.secho(f"❌ Push failed: {error}", fg="red")
                return

            staged_skill.copy_to(skill_path)

        click.secho(f"✅ Successfully pushed {skill_name} v{new_version}", fg="green", bold=True)

    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")


@cli.command()
@click.argument("skill_name")
@click.option(
    "--agent",
    type=click.Choice(list_providers(), case_sensitive=False),
    help="Agent context (claude, codex, gemini)"
)
@click.option("--provider", hidden=True, help="Deprecated alias for --agent")
def update(skill_name, agent, provider):
    """Update an installed skill to the latest version.

    \b
    Examples:
      skillex update python-testing
      skillex update quant-connect --provider claude
    """
    check_for_updates_quietly()

    # Detect provider
    agent = resolve_agent(agent, provider)

    if not agent:
        click.secho("❌ Could not detect agent. Use --agent flag", fg="red")
        return

    provider_obj = get_provider(agent)
    if not provider_obj:
        click.secho(f"❌ Unknown agent: {agent}", fg="red")
        return

    repo = get_repo()
    skills_dir = provider_obj.get_skills_directory()
    installer = InstallManager(repo)

    click.echo(f"Updating {skill_name} in {agent}...")

    success, error = installer.update_skill(skill_name, skills_dir)

    if success:
        if "already at latest" in (error or ""):
            click.echo(error)
        else:
            click.secho(f"✅ Successfully updated {skill_name}", fg="green")
    else:
        click.secho(f"❌ Failed: {error}", fg="red")


@cli.command()
@click.argument("skill_name")
@click.confirmation_option(prompt="Are you sure you want to delete this skill?")
def delete(skill_name):
    """Delete a skill from the repository.

    This removes the skill from the central repository. Installed copies
    in provider directories are not automatically removed.

    \b
    Examples:
      skillex delete old-skill
    """
    repo = get_repo()

    click.echo(f"Deleting {skill_name} from repository...")

    success, error = repo.delete_skill(skill_name)

    if success:
        click.secho(f"✅ Successfully deleted {skill_name}", fg="green")
        click.echo("\nNote: Skill still exists in provider directories.")
        click.echo("Remove manually if needed.")
    else:
        click.secho(f"❌ Failed: {error}", fg="red")


@cli.command()
@click.option(
    "--from",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Source directory containing skills to migrate"
)
@click.option(
    "--default-version",
    default="0.1.0",
    help="Default version for skills without version info"
)
@click.option(
    "--provider",
    type=click.Choice(list_providers(), case_sensitive=False),
    default="claude",
    help="Provider to assign to migrated skills"
)
def migrate(source_dir, default_version, provider):
    """Migrate existing skills from another directory.

    Copies skills from a source directory (e.g., agent-cubicle/skills)
    to ~/.skillex/skills/, creating skill.json metadata for each.

    \b
    Examples:
      skillex migrate --from ~/repos/agent-cubicle/skills
      skillex migrate --from ~/repos/agent-cubicle/skills --provider claude
    """
    repo = get_repo()

    click.echo(f"Migrating skills from: {source_dir}")
    click.echo(f"To: {repo.skills_path}\n")

    # Find all skill directories (those with SKILL.md)
    skill_dirs = [d for d in source_dir.iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists()]

    if not skill_dirs:
        click.secho("❌ No skills found (looking for directories with SKILL.md)", fg="red")
        return

    click.echo(f"Found {len(skill_dirs)} skill(s):\n")

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        click.echo(f"  - {skill_name}")

    click.echo()

    if not click.confirm("Proceed with migration?"):
        click.echo("Migration cancelled")
        return

    # Migrate each skill
    migrated = []

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        dest_dir = repo.skills_path / skill_name

        click.echo(f"\nMigrating {skill_name}...")

        try:
            # Copy skill directory
            if dest_dir.exists():
                click.echo(f"  Skill already exists, skipping...")
                continue

            import shutil
            shutil.copytree(skill_dir, dest_dir)

            # Create skill.json if it doesn't exist
            skill_json_path = dest_dir / "skill.json"

            if not skill_json_path.exists():
                # Create minimal skill.json
                temp_skill = Skill.__new__(Skill)
                temp_skill.path = dest_dir

                skill_hash = temp_skill.compute_hash()

                skill_json = {
                    "name": skill_name,
                    "version": default_version,
                    "hash": skill_hash,
                    "dependencies": [],
                    "created": datetime.now().isoformat(),
                    "updated": datetime.now().isoformat(),
                    "author": "migrated",
                    "description": f"Migrated from {source_dir.name}"
                }

                with open(skill_json_path, "w") as f:
                    json.dump(skill_json, f, indent=2)

                click.echo(f"  ✓ Created skill.json")

            migrated.append(skill_name)
            click.secho(f"  ✓ Migrated successfully", fg="green")

        except Exception as e:
            click.secho(f"  ✗ Failed: {e}", fg="red")

    # Commit to repository
    if migrated:
        click.echo(f"\nCommitting {len(migrated)} migrated skill(s) to repository...")

        try:
            repo.repo.index.add([str(repo.skills_path)])
            repo.repo.index.commit(
                f"chore: migrate {len(migrated)} skills from {source_dir.name}\n\n"
                f"Migrated skills:\n" + "\n".join(f"- {s}" for s in migrated)
            )

            click.secho(f"\n✅ Successfully migrated {len(migrated)} skill(s)!", fg="green", bold=True)
            click.echo(f"\nMigrated skills: {', '.join(migrated)}")
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review skills in: {repo.skills_path}")
            click.echo(f"  2. Push to remote: cd {repo.repo_path} && git push")
            click.echo(f"  3. Install to provider: skillex pull <skill-name>")

        except Exception as e:
            click.secho(f"❌ Failed to commit: {e}", fg="red")
    else:
        click.echo("\nNo skills were migrated")


@cli.group()
def config():
    """Manage skillex configuration.

    Configure remote repository URL, view settings, etc.

    \b
    Examples:
      skillex config show                     # Show all configuration
      skillex config set-remote <url>         # Set remote repository URL
      skillex config get-remote               # Show remote URL
    """
    pass


@config.command()
def show():
    """Show all configuration settings."""
    repo = SkillexRepository()
    try:
        repo.initialize()
    except ValueError:
        repo = None

    click.secho("\nSkillex Configuration", bold=True)
    repo_path = Path.home() / ".skillex"
    click.echo(f"Repository path: {repo_path}")
    click.echo(f"Skills path: {repo_path / 'skills'}")

    # Show remote URL
    try:
        if repo and repo.repo and repo.repo.remotes:
            remote = repo.repo.remote("origin")
            click.echo(f"Remote URL: {remote.url}")
        else:
            click.echo("Remote URL: (not configured)")
    except:
        click.echo("Remote URL: (not configured)")

    # Show config file if exists
    if repo:
        skills = repo.get_all_skills()
        click.echo(f"\nTotal skills: {len(skills)}")
    else:
        click.echo("\nTotal skills: repository not cloned yet")

    # Show providers
    click.echo("\nProviders:")
    for provider_name in list_providers():
        provider = get_provider(provider_name)
        skills_dir = provider.get_skills_directory()
        exists = "✓" if skills_dir.exists() else "✗"
        click.echo(f"  {exists} {provider_name}: {skills_dir}")


@config.command()
@click.argument("url")
def set_remote(url):
    """Set the remote repository URL.

    \b
    Examples:
      skillex config set-remote https://github.com/user/my-skills.git
      skillex config set-remote git@github.com:user/my-skills.git
    """
    global _repo
    repo = SkillexRepository()

    try:
        if repo.repo_path.exists():
            repo.initialize()
            try:
                origin = repo.repo.remote("origin")
                origin.set_url(url)
                click.secho("✓ Updated remote URL", fg="green")
            except ValueError:
                repo.repo.create_remote("origin", url)
                click.secho("✓ Created remote 'origin'", fg="green")
        else:
            click.echo(f"Cloning {url} into {repo.repo_path}...")
            repo.initialize(remote_url=url)
            click.secho("✓ Cloned remote repository", fg="green")

        _repo = repo
        click.echo(f"Remote URL: {url}")
        click.echo(f"Repository path: {repo.repo_path}")

    except Exception as e:
        click.secho(f"❌ Failed to set remote: {e}", fg="red")


@config.command()
def get_remote():
    """Show the current remote repository URL."""
    repo = SkillexRepository()

    try:
        repo.initialize()
        if repo.repo and repo.repo.remotes:
            remote = repo.repo.remote("origin")
            click.echo(f"Remote URL: {remote.url}")
        else:
            click.secho("No remote configured", fg="yellow")
            click.echo("\nTo set a remote, run:")
            click.echo("  skillex config set-remote <url>")
    except Exception as e:
        click.secho(f"No remote configured: {e}", fg="yellow")
        click.echo("\nTo set a remote, run:")
        click.echo("  skillex config set-remote <url>")


if __name__ == "__main__":
    cli()
