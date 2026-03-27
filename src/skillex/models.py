"""Core data models for skillex.

This module defines the data structures used throughout the skillex system:
- SkillMetadata: Represents the skill.json metadata file
- SkillLockEntry: Individual skill entry in .skillex.lock
- SkillLock: Complete .skillex.lock file structure
- CommitType: Enum for git commit types
- Skill: Main class for managing skill directories and operations
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
import json
import hashlib
import shutil

from pydantic import BaseModel, Field


class CommitType(str, Enum):
    """Valid commit types for structured commit messages."""

    FEAT = "feat"       # New capability
    FIX = "fix"         # Bug fix
    REFACTOR = "refactor"  # No behavior change
    DOCS = "docs"       # Metadata / description only
    TEST = "test"       # Test changes
    CHORE = "chore"     # Infra / formatting


class SkillMetadata(BaseModel):
    """Represents the skill.json metadata file for a skill.

    Each skill directory contains a skill.json file with this structure.
    The hash field is used to detect changes to the skill content.

    Attributes:
        name: Skill name (lowercase, alphanumeric, hyphens only)
        version: Semantic version (e.g., "0.1.0")
        hash: SHA256 hash of skill content (for change detection)
        dependencies: List of skill names this skill depends on
        created: ISO timestamp when skill was created
        updated: ISO timestamp of last modification
        author: Author identifier (default: "agent")
        description: Human-readable skill description
    """

    name: str = Field(pattern=r"^[a-z0-9\-]+$")
    version: str
    hash: str
    dependencies: List[str] = Field(default_factory=list)
    created: datetime
    updated: datetime
    author: str = "agent"
    description: str


class SkillLockEntry(BaseModel):
    """Entry in .skillex.lock file for a single installed skill.

    Tracks the installed version and state of a skill in an agent directory.

    Attributes:
        version: Semantic version installed
        hash: SHA256 hash of installed content
        installed: ISO timestamp when installed
        source: Absolute path to source in ~/.skillex/skills/
    """

    version: str
    hash: str
    installed: datetime
    source: str


class SkillLock(BaseModel):
    """Complete .skillex.lock file structure.

    This file exists in each agent directory (e.g., ~/.claude/skills/.skillex.lock)
    and tracks all installed skills and their versions.

    Attributes:
        version: Lockfile format version
        updated: Last update timestamp
        skills: Dict mapping skill names to their lock entries
    """

    version: str = "1.0"
    updated: datetime
    skills: dict[str, SkillLockEntry] = Field(default_factory=dict)


class Skill:
    """Manages a skill directory and its operations.

    A skill is a directory containing:
    - skill.json: Metadata (SkillMetadata)
    - SKILL.md: Main skill content
    - Optional subdirectories: references/, examples/, agents/

    Example:
        >>> skill = Skill(Path("~/.skillex/skills/python-testing"))
        >>> skill.metadata.name
        'python-testing'
        >>> skill.compute_hash()
        'sha256:abc123...'
        >>> skill.copy_to(Path("~/.claude/skills/python-testing"))
    """

    def __init__(self, path: Path):
        """Initialize a Skill from a directory path.

        Args:
            path: Absolute path to skill directory

        Raises:
            ValueError: If skill directory doesn't exist
            ValueError: If skill.json is missing or invalid
        """
        self.path = path.resolve()

        if not self.path.exists():
            raise ValueError(f"Skill directory does not exist: {self.path}")

        if not self.path.is_dir():
            raise ValueError(f"Skill path is not a directory: {self.path}")

        self.metadata = self._load_metadata()

    def _load_metadata(self) -> SkillMetadata:
        """Load and parse skill.json metadata.

        Returns:
            Parsed SkillMetadata object

        Raises:
            ValueError: If skill.json is missing or invalid
        """
        metadata_path = self.path / "skill.json"

        if not metadata_path.exists():
            raise ValueError(f"skill.json not found in {self.path}")

        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)

            # Convert ISO strings to datetime objects
            if isinstance(data.get("created"), str):
                data["created"] = datetime.fromisoformat(data["created"])
            if isinstance(data.get("updated"), str):
                data["updated"] = datetime.fromisoformat(data["updated"])

            return SkillMetadata(**data)
        except Exception as e:
            raise ValueError(f"Invalid skill.json in {self.path}: {e}")

    def save_metadata(self) -> None:
        """Write current metadata to skill.json.

        Updates the 'updated' timestamp to current time.
        """
        metadata_path = self.path / "skill.json"

        # Update the timestamp
        self.metadata.updated = datetime.now()

        # Convert to dict and handle datetime serialization
        data = self.metadata.model_dump()
        data["created"] = data["created"].isoformat()
        data["updated"] = data["updated"].isoformat()

        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)

    def compute_hash(self) -> str:
        """Compute SHA256 hash of all files in skill directory.

        Excludes skill.json itself to avoid circular dependency.
        Hash is deterministic (files processed in sorted order).

        Returns:
            Hash string in format "sha256:hexdigest"
        """
        hasher = hashlib.sha256()

        # Get all files except skill.json, sorted for consistency
        files = sorted([
            f for f in self.path.rglob("*")
            if f.is_file() and f.name != "skill.json"
        ])

        for file_path in files:
            # Include relative path in hash for structure changes
            rel_path = file_path.relative_to(self.path)
            hasher.update(str(rel_path).encode("utf-8"))

            # Include file content
            with open(file_path, "rb") as f:
                hasher.update(f.read())

        return f"sha256:{hasher.hexdigest()}"

    def copy_to(self, dest: Path) -> None:
        """Copy skill to destination directory.

        Overwrites destination if it exists. Performs a complete
        recursive copy of all files and subdirectories.

        Args:
            dest: Destination path (will be created if needed)
        """
        # Remove existing destination
        if dest.exists():
            shutil.rmtree(dest)

        # Create parent directory if needed
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy entire skill directory
        shutil.copytree(self.path, dest)

    def copy_from(self, source: Path) -> None:
        """Copy skill from source directory to this skill's path.

        Used when pushing changes from an agent directory back to ~/.skillex.
        Updates the hash in metadata after copying.

        Args:
            source: Source skill directory path
        """
        # Remove current directory
        if self.path.exists():
            shutil.rmtree(self.path)

        # Create parent directory if needed
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Copy from source
        shutil.copytree(source, self.path)

        # Reload metadata and update hash
        self.metadata = self._load_metadata()
        new_hash = self.compute_hash()
        self.metadata.hash = new_hash
        self.save_metadata()

    def __repr__(self) -> str:
        """String representation of Skill."""
        return f"Skill(name='{self.metadata.name}', version='{self.metadata.version}')"
