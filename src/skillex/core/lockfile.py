"""Lockfile management for tracking installed skills.

Each agent directory (e.g., ~/.claude/skills/) contains a .skillex.lock file
that tracks which skills are installed and their versions.

This enables:
- Detection of version drift between installations
- Tracking of last installation time
- Verification of content integrity via hashes
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from ..models import Skill, SkillLock, SkillLockEntry


class LockfileManager:
    """Manages .skillex.lock files in agent directories.

    The lockfile tracks all installed skills, their versions, hashes,
    and installation timestamps.

    Example:
        >>> manager = LockfileManager(Path("~/.claude/skills"))
        >>> lock = manager.load()
        >>> manager.update_entry("python-testing", "0.2.1", "sha256:abc...", "/path/to/source")
        >>> manager.save(lock)
        >>> installed_version = manager.get_installed_version("python-testing")
        >>> print(installed_version)
        '0.2.1'
    """

    def __init__(self, agent_dir: Path):
        """Initialize lockfile manager for an agent directory.

        Args:
            agent_dir: Path to agent skills directory (e.g., ~/.claude/skills)
        """
        self.agent_dir = agent_dir.resolve()
        self.lockfile_path = self.agent_dir / ".skillex.lock"

    def load(self) -> SkillLock:
        """Load lockfile or create empty one if it doesn't exist.

        Returns:
            SkillLock object with current state

        Example:
            >>> lock = manager.load()
            >>> print(lock.skills.keys())
            dict_keys(['python-testing', 'quant-connect'])
        """
        if self.lockfile_path.exists():
            try:
                with open(self.lockfile_path, "r") as f:
                    data = json.load(f)

                # Convert ISO timestamp strings to datetime objects
                data["updated"] = datetime.fromisoformat(data["updated"])

                for skill_name, entry_data in data.get("skills", {}).items():
                    entry_data["installed"] = datetime.fromisoformat(entry_data["installed"])

                lock = SkillLock(**data)
                if self._lockfile_needs_rebuild(lock):
                    print(f"Warning: Lockfile at {self.lockfile_path} is behind installed skills, rebuilding")
                    return self.rebuild()
                return lock
            except Exception as e:
                # If lockfile is corrupted, create a new one
                print(f"Warning: Corrupted lockfile at {self.lockfile_path}, rebuilding: {e}")
                return self.rebuild()
        else:
            # Create new empty lockfile
            return self.rebuild()

    def _iter_installed_skill_dirs(self) -> list[Path]:
        """Return installed skill directories that contain skill metadata."""
        if not self.agent_dir.exists():
            return []

        return sorted(
            path for path in self.agent_dir.iterdir()
            if path.is_dir() and (path / "skill.json").exists()
        )

    def _lockfile_needs_rebuild(self, lock: SkillLock) -> bool:
        """Return True if the lockfile is missing installed skill directories."""
        installed_skill_names = {
            skill_dir.name for skill_dir in self._iter_installed_skill_dirs()
        }
        locked_skill_names = set(lock.skills.keys())
        return installed_skill_names != locked_skill_names

    def rebuild(self) -> SkillLock:
        """Rebuild the lockfile from installed skill directories on disk."""
        lock = SkillLock(updated=datetime.now(), skills={})

        for skill_dir in self._iter_installed_skill_dirs():
            skill = Skill(skill_dir)
            lock.skills[skill.metadata.name] = SkillLockEntry(
                version=skill.metadata.version,
                hash=skill.compute_hash(),
                installed=datetime.now(),
                source="recovered-from-installed-skill",
            )

        self.save(lock)
        return lock

    def save(self, lock: SkillLock) -> None:
        """Save lockfile to disk.

        Updates the 'updated' timestamp to current time.

        Args:
            lock: SkillLock object to save
        """
        # Ensure agent directory exists
        self.agent_dir.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        lock.updated = datetime.now()

        # Convert to dict for JSON serialization
        data = lock.model_dump()

        # Convert datetime objects to ISO strings
        data["updated"] = data["updated"].isoformat()
        for skill_name in data["skills"]:
            data["skills"][skill_name]["installed"] = (
                data["skills"][skill_name]["installed"].isoformat()
            )

        # Write to file with pretty formatting
        with open(self.lockfile_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_installed_version(self, skill_name: str) -> Optional[str]:
        """Get installed version of a skill.

        Args:
            skill_name: Name of skill to check

        Returns:
            Version string if installed, None otherwise

        Example:
            >>> manager.get_installed_version("python-testing")
            '0.2.1'
            >>> manager.get_installed_version("nonexistent-skill")
            None
        """
        lock = self.load()
        entry = lock.skills.get(skill_name)
        return entry.version if entry else None

    def get_installed_hash(self, skill_name: str) -> Optional[str]:
        """Get installed hash of a skill.

        Args:
            skill_name: Name of skill to check

        Returns:
            Hash string if installed, None otherwise
        """
        lock = self.load()
        entry = lock.skills.get(skill_name)
        return entry.hash if entry else None

    def is_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed.

        Args:
            skill_name: Name of skill to check

        Returns:
            True if installed, False otherwise
        """
        lock = self.load()
        return skill_name in lock.skills

    def update_entry(
        self,
        skill_name: str,
        version: str,
        hash: str,
        source: str
    ) -> None:
        """Update or add a skill entry in the lockfile.

        Creates a new entry if the skill isn't installed, or updates
        the existing entry.

        Args:
            skill_name: Name of skill
            version: Semantic version string
            hash: SHA256 hash of skill content
            source: Absolute path to source in ~/.skillex/skills/

        Example:
            >>> manager.update_entry(
            ...     "python-testing",
            ...     "0.2.1",
            ...     "sha256:abc123...",
            ...     "/Users/user/.skillex/skills/python-testing"
            ... )
        """
        lock = self.load()

        # Create new entry
        lock.skills[skill_name] = SkillLockEntry(
            version=version,
            hash=hash,
            installed=datetime.now(),
            source=source
        )

        # Save updated lockfile
        self.save(lock)

    def remove_entry(self, skill_name: str) -> bool:
        """Remove a skill entry from the lockfile.

        Args:
            skill_name: Name of skill to remove

        Returns:
            True if skill was removed, False if it wasn't installed

        Example:
            >>> manager.remove_entry("python-testing")
            True
            >>> manager.remove_entry("nonexistent-skill")
            False
        """
        lock = self.load()

        if skill_name in lock.skills:
            del lock.skills[skill_name]
            self.save(lock)
            return True

        return False

    def list_installed(self) -> list[tuple[str, str]]:
        """Get list of all installed skills with their versions.

        Returns:
            List of (skill_name, version) tuples

        Example:
            >>> manager.list_installed()
            [('python-testing', '0.2.1'), ('quant-connect', '0.1.5')]
        """
        lock = self.load()
        return [(name, entry.version) for name, entry in lock.skills.items()]

    def get_entry(self, skill_name: str) -> Optional[SkillLockEntry]:
        """Get full lockfile entry for a skill.

        Args:
            skill_name: Name of skill

        Returns:
            SkillLockEntry if installed, None otherwise
        """
        lock = self.load()
        return lock.skills.get(skill_name)
