"""Repository management for the ~/.skillex clone/worktree."""

from pathlib import Path
from typing import Optional
import git
from ..models import Skill


class SkillexRepository:
    """Manages the ~/.skillex git repository.

    This is the central repository where all skills are stored.
    Skills are organized in ~/.skillex/skills/<skill-name>/.

    Example:
        >>> repo = SkillexRepository()
        >>> repo.initialize()
        >>> skill = repo.get_skill("python-testing")
        >>> repo.push("python-testing", "feat: add new test helper")
        >>> repo.pull()
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize repository manager.

        Args:
            repo_path: Path to repository (defaults to ~/.skillex)
        """
        self.repo_path = (repo_path or Path.home() / ".skillex").resolve()
        self.skills_path = self.repo_path / "skills"
        self.config_dir = self.repo_path / ".skillex"
        self.config_path = self.config_dir / "config.json"
        self.repo: Optional[git.Repo] = None

    def initialize(self, remote_url: Optional[str] = None) -> None:
        """Load an existing ~/.skillex clone or clone it from a remote URL."""
        if self.repo_path.exists():
            try:
                self.repo = git.Repo(self.repo_path)
            except git.exc.InvalidGitRepositoryError:
                raise ValueError(f"{self.repo_path} exists but is not a git repository")
        elif remote_url:
            self.clone_from_remote(remote_url)
        else:
            raise ValueError(
                "Skillex repository not found at ~/.skillex. "
                "Run 'skillex config set-remote <url>' first."
            )

        self.skills_path.mkdir(parents=True, exist_ok=True)

    def clone_from_remote(self, remote_url: str) -> None:
        """Clone the remote skills repository into ~/.skillex."""
        if self.repo_path.exists():
            raise ValueError(f"{self.repo_path} already exists")

        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        self.repo = git.Repo.clone_from(remote_url, self.repo_path)
        self.skills_path.mkdir(parents=True, exist_ok=True)

    def _get_origin_remote(self) -> Optional[git.Remote]:
        """Return the origin remote if configured."""
        if not self.repo:
            return None

        try:
            return self.repo.remote("origin")
        except ValueError:
            return None

    def _get_active_branch_name(self) -> str:
        """Return the current local branch name."""
        if not self.repo:
            return "main"

        try:
            return self.repo.active_branch.name
        except TypeError:
            return "main"

    def is_behind_remote(self) -> bool:
        """Check if local repository is behind the remote.

        Returns:
            True if local is behind remote, False otherwise

        Example:
            >>> if repo.is_behind_remote():
            ...     print("Local is behind, pull first!")
        """
        if not self.repo:
            return False

        origin = self._get_origin_remote()
        if origin is None:
            return False

        try:
            # Fetch latest from remote
            origin.fetch()

            # Get local and remote commits
            local_commit = self.repo.head.commit
            try:
                remote_commit = self.repo.commit(f"origin/{self._get_active_branch_name()}")
            except Exception:
                # Fall back to common default names
                try:
                    remote_commit = self.repo.commit("origin/main")
                except Exception:
                    try:
                        remote_commit = self.repo.commit("origin/master")
                    except Exception:
                    # No remote branch exists yet
                        return False

            # Check if local is ancestor of remote
            merge_base = self.repo.merge_base(local_commit, remote_commit)

            if merge_base and merge_base[0] == local_commit and local_commit != remote_commit:
                return True

            return False

        except git.exc.GitCommandError:
            # No remote or network error
            return False

    def pull(self, skill_name: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """Pull updates from remote with automatic rebasing.

        Attempts to automatically rebase local changes on top of remote changes.
        If conflicts occur, provides clear error message.

        Args:
            skill_name: Optional specific skill to pull (currently pulls all)

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = repo.pull()
            >>> if not success:
            ...     print(f"Pull failed: {error}")
        """
        if not self.repo:
            return False, "Repository not initialized"

        origin = self._get_origin_remote()
        if origin is None:
            return False, (
                "No remote configured. Set one with:\n"
                "  skillex config set-remote <url>"
            )

        try:
            # Check if there are uncommitted changes
            if self.repo.is_dirty():
                # Stash changes
                self.repo.git.stash("save", "skillex auto-stash before pull")
                stashed = True
            else:
                stashed = False

            # Fetch from remote
            origin.fetch()

            # Determine default branch
            default_branch = self._get_active_branch_name()
            try:
                self.repo.commit(f"origin/{default_branch}")
            except Exception:
                try:
                    self.repo.commit("origin/main")
                    default_branch = "main"
                except Exception:
                    default_branch = "master"

            # Pull with rebase
            try:
                self.repo.git.pull("--rebase", "origin", default_branch)

                # If we stashed, try to apply stash
                if stashed:
                    try:
                        self.repo.git.stash("pop")
                    except git.exc.GitCommandError as e:
                        return False, (
                            "Pulled successfully but could not apply stashed changes. "
                            f"Conflicts detected:\n{e}\n\n"
                            f"Please resolve manually in {self.repo_path}"
                        )

                return True, None

            except git.exc.GitCommandError as e:
                error_msg = str(e)

                # If rebase failed, abort it
                try:
                    self.repo.git.rebase("--abort")
                except:
                    pass

                # Restore stashed changes if needed
                if stashed:
                    try:
                        self.repo.git.stash("pop")
                    except:
                        pass

                return False, f"Rebase failed. Conflicts detected:\n{error_msg}\n\nPlease resolve manually."

        except Exception as e:
            return False, f"Pull failed: {e}"

    def push(self, skill_name: str, commit_message: str) -> tuple[bool, Optional[str]]:
        """Push skill changes to remote repository.

        Stages the skill directory, creates a commit, and pushes to remote.
        Checks if local is behind remote before pushing.

        Args:
            skill_name: Name of skill to push
            commit_message: Formatted commit message

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = repo.push("python-testing", "feat: add new helper")
            >>> if not success:
            ...     print(f"Push failed: {error}")
        """
        if not self.repo:
            return False, "Repository not initialized"

        origin = self._get_origin_remote()
        if origin is None:
            return False, (
                "No remote configured. Set one with:\n"
                "  skillex config set-remote <url>"
            )

        # Check if behind remote
        if self.is_behind_remote():
            return False, (
                "Local repository is behind remote. Pull first:\n"
                f"  skillex pull"
            )

        try:
            # Stage skill directory
            skill_path = self.skills_path / skill_name
            if not skill_path.exists():
                return False, f"Skill directory not found: {skill_path}"

            # Add all files in skill directory
            self.repo.index.add([str(skill_path)])

            # Create commit
            self.repo.index.commit(commit_message)

            # Push current branch to remote
            branch_name = self._get_active_branch_name()
            origin.push(branch_name)

            return True, None

        except git.exc.GitCommandError as e:
            return False, f"Push failed: {e}"

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill from the repository.

        Args:
            name: Skill name

        Returns:
            Skill object if found, None otherwise

        Example:
            >>> skill = repo.get_skill("python-testing")
            >>> if skill:
            ...     print(skill.metadata.version)
        """
        skill_path = self.skills_path / name

        if not skill_path.exists():
            return None

        try:
            return Skill(skill_path)
        except ValueError:
            # Invalid skill directory
            return None

    def get_all_skills(self) -> list[Skill]:
        """Get all skills from the repository.

        Returns:
            List of Skill objects

        Example:
            >>> skills = repo.get_all_skills()
            >>> for skill in skills:
            ...     print(f"{skill.metadata.name} v{skill.metadata.version}")
        """
        if not self.skills_path.exists():
            return []

        skills = []
        for skill_dir in self.skills_path.iterdir():
            if skill_dir.is_dir():
                try:
                    skill = Skill(skill_dir)
                    skills.append(skill)
                except ValueError:
                    # Invalid skill directory, skip
                    continue

        return skills

    def delete_skill(self, name: str) -> tuple[bool, Optional[str]]:
        """Delete a skill from the repository.

        Removes the skill directory and commits the deletion.

        Args:
            name: Skill name

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = repo.delete_skill("old-skill")
            >>> if success:
            ...     print("Skill deleted successfully")
        """
        if not self.repo:
            return False, "Repository not initialized"

        skill_path = self.skills_path / name

        if not skill_path.exists():
            return False, f"Skill '{name}' not found"

        try:
            # Remove from git
            self.repo.index.remove([str(skill_path)], r=True)

            # Delete directory
            import shutil
            shutil.rmtree(skill_path)

            # Commit deletion
            self.repo.index.commit(f"chore({name}): delete skill")

            return True, None

        except Exception as e:
            return False, f"Failed to delete skill: {e}"

    def check_for_updates(self) -> tuple[bool, list[str]]:
        """Check if there are updates available from remote.

        Fetches from remote and compares with local state.

        Returns:
            Tuple of (has_updates, list_of_updated_skills)

        Example:
            >>> has_updates, updated_skills = repo.check_for_updates()
            >>> if has_updates:
            ...     print(f"Updates available for: {', '.join(updated_skills)}")
        """
        if not self.repo:
            return False, []

        origin = self._get_origin_remote()
        if origin is None:
            return False, []

        try:
            # Fetch from remote
            origin.fetch()

            # Compare local and remote
            if self.is_behind_remote():
                # For now, return generic message
                # Could be enhanced to list specific skills
                return True, ["(check with pull for details)"]

            return False, []

        except:
            return False, []
