"""Installation management for skills to agent directories.

Handles copying skills from ~/.skillex to agent directories (e.g., ~/.claude/skills)
and vice versa, with version tracking via lockfiles.
"""

from pathlib import Path
from typing import Optional

from .repository import SkillexRepository
from .lockfile import LockfileManager
from ..models import Skill


class InstallManager:
    """Manages skill installation to agent directories.

    Coordinates copying skills from the central repository to provider
    directories, and tracks installed versions via lockfiles.

    Example:
        >>> repo = SkillexRepository()
        >>> installer = InstallManager(repo)
        >>> installer.install_skill("python-testing", "claude", Path("~/.claude/skills"))
        >>> installer.update_skill("python-testing", Path("~/.claude/skills"))
    """

    def __init__(self, repo: SkillexRepository):
        """Initialize install manager.

        Args:
            repo: SkillexRepository instance
        """
        self.repo = repo

    def install_skill(
        self,
        skill_name: str,
        provider: str,
        agent_dir: Path
    ) -> tuple[bool, Optional[str]]:
        """Install a skill from repository to agent directory.

        Copies skill files and updates the agent's lockfile.

        Args:
            skill_name: Name of skill to install
            provider: Provider name (claude, codex, gemini)
            agent_dir: Path to agent's skills directory

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = installer.install_skill(
            ...     "python-testing",
            ...     "claude",
            ...     Path("~/.claude/skills")
            ... )
            >>> if success:
            ...     print("Skill installed successfully")
        """
        # Ensure agent directory exists
        agent_dir = agent_dir.resolve()
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Get skill from repository
        skill = self.repo.get_skill(skill_name)
        if not skill:
            return False, f"Skill '{skill_name}' not found in repository"

        try:
            # Copy skill to agent directory
            dest = agent_dir / skill_name
            skill.copy_to(dest)

            # Update lockfile
            lockfile = LockfileManager(agent_dir)
            lockfile.update_entry(
                skill_name,
                skill.metadata.version,
                skill.metadata.hash,
                str(skill.path)
            )

            return True, None

        except Exception as e:
            return False, f"Failed to install skill: {e}"

    def update_skill(
        self,
        skill_name: str,
        agent_dir: Path
    ) -> tuple[bool, Optional[str]]:
        """Update an installed skill to latest version from repository.

        Checks if update is needed, then copies latest version and updates lockfile.

        Args:
            skill_name: Name of skill to update
            agent_dir: Path to agent's skills directory

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = installer.update_skill("python-testing", Path("~/.claude/skills"))
            >>> if success:
            ...     print("Skill updated successfully")
        """
        agent_dir = agent_dir.resolve()

        # Check lockfile for current version
        lockfile = LockfileManager(agent_dir)
        current_version = lockfile.get_installed_version(skill_name)

        if not current_version:
            return False, f"Skill '{skill_name}' is not installed. Use 'skillex pull' instead."

        # Get latest from repository
        skill = self.repo.get_skill(skill_name)
        if not skill:
            return False, f"Skill '{skill_name}' not found in repository"

        # Check if update needed
        if current_version == skill.metadata.version:
            # Check hash to detect manual edits
            current_hash = lockfile.get_installed_hash(skill_name)
            if current_hash == skill.metadata.hash:
                return True, f"Skill '{skill_name}' already at latest version {current_version}"

        try:
            # Copy updated skill
            dest = agent_dir / skill_name
            skill.copy_to(dest)

            # Update lockfile
            lockfile.update_entry(
                skill_name,
                skill.metadata.version,
                skill.metadata.hash,
                str(skill.path)
            )

            return True, None

        except Exception as e:
            return False, f"Failed to update skill: {e}"

    def uninstall_skill(
        self,
        skill_name: str,
        agent_dir: Path
    ) -> tuple[bool, Optional[str]]:
        """Uninstall a skill from agent directory.

        Removes skill directory and updates lockfile.

        Args:
            skill_name: Name of skill to uninstall
            agent_dir: Path to agent's skills directory

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = installer.uninstall_skill("python-testing", Path("~/.claude/skills"))
            >>> if success:
            ...     print("Skill uninstalled successfully")
        """
        agent_dir = agent_dir.resolve()
        skill_path = agent_dir / skill_name

        if not skill_path.exists():
            return False, f"Skill '{skill_name}' is not installed"

        try:
            # Remove directory
            import shutil
            shutil.rmtree(skill_path)

            # Update lockfile
            lockfile = LockfileManager(agent_dir)
            lockfile.remove_entry(skill_name)

            return True, None

        except Exception as e:
            return False, f"Failed to uninstall skill: {e}"

    def check_updates(self, agent_dir: Path) -> list[tuple[str, str, str]]:
        """Check which installed skills have updates available.

        Compares installed versions with repository versions.

        Args:
            agent_dir: Path to agent's skills directory

        Returns:
            List of (skill_name, installed_version, latest_version) tuples

        Example:
            >>> updates = installer.check_updates(Path("~/.claude/skills"))
            >>> for name, installed, latest in updates:
            ...     print(f"{name}: {installed} -> {latest}")
        """
        agent_dir = agent_dir.resolve()
        lockfile = LockfileManager(agent_dir)

        updates = []

        for skill_name, installed_version in lockfile.list_installed():
            # Get latest from repository
            skill = self.repo.get_skill(skill_name)
            if not skill:
                continue

            # Compare versions
            if installed_version != skill.metadata.version:
                updates.append((skill_name, installed_version, skill.metadata.version))
            else:
                # Check hash for manual edits
                installed_hash = lockfile.get_installed_hash(skill_name)
                if installed_hash and installed_hash != skill.metadata.hash:
                    updates.append((skill_name, installed_version, skill.metadata.version))

        return updates

    def detect_changes(
        self,
        skill_name: str,
        agent_dir: Path
    ) -> tuple[bool, Optional[str]]:
        """Detect if installed skill has local changes vs repository.

        Compares hash of installed skill with repository version.

        Args:
            skill_name: Name of skill to check
            agent_dir: Path to agent's skills directory

        Returns:
            Tuple of (has_changes, description)

        Example:
            >>> has_changes, desc = installer.detect_changes("python-testing", Path("~/.claude/skills"))
            >>> if has_changes:
            ...     print(f"Local changes detected: {desc}")
        """
        agent_dir = agent_dir.resolve()
        skill_path = agent_dir / skill_name

        if not skill_path.exists():
            return False, "Skill not installed"

        try:
            # Load installed skill
            installed_skill = Skill(skill_path)

            # Get repository version
            repo_skill = self.repo.get_skill(skill_name)
            if not repo_skill:
                return False, "Skill not found in repository"

            # Compare hashes
            installed_hash = installed_skill.compute_hash()
            repo_hash = repo_skill.metadata.hash

            if installed_hash != repo_hash:
                # Check if version also differs
                if installed_skill.metadata.version != repo_skill.metadata.version:
                    return True, (
                        f"Version mismatch: installed v{installed_skill.metadata.version}, "
                        f"repository v{repo_skill.metadata.version}"
                    )
                else:
                    return True, "Local modifications detected (hash mismatch)"

            return False, "No changes detected"

        except Exception as e:
            return False, f"Error checking changes: {e}"
