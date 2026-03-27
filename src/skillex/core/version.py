"""Semantic version management utilities.

Handles parsing, comparison, and bumping of semantic versions.
Uses the `packaging` library for robust version handling.
"""

from packaging.version import Version, parse
from typing import Literal


BumpType = Literal["major", "minor", "patch"]


class VersionManager:
    """Manages skill versions using semantic versioning (semver).

    Provides utilities for parsing, comparing, and bumping version strings.

    Example:
        >>> VersionManager.parse("1.2.3")
        <Version('1.2.3')>
        >>> VersionManager.bump("1.2.3", "minor")
        '1.3.0'
        >>> VersionManager.compare("1.2.3", "1.2.4")
        -1
    """

    @staticmethod
    def parse(version_str: str) -> Version:
        """Parse a semantic version string.

        Args:
            version_str: Version string (e.g., "1.2.3")

        Returns:
            Parsed Version object

        Raises:
            packaging.version.InvalidVersion: If version string is invalid

        Example:
            >>> v = VersionManager.parse("1.2.3")
            >>> v.major
            1
            >>> v.minor
            2
            >>> v.micro
            3
        """
        return parse(version_str)

    @staticmethod
    def bump(version: str, bump_type: BumpType) -> str:
        """Bump version by major, minor, or patch.

        Args:
            version: Current version string (e.g., "1.2.3")
            bump_type: Type of bump ("major", "minor", or "patch")

        Returns:
            New version string

        Raises:
            ValueError: If bump_type is invalid

        Example:
            >>> VersionManager.bump("1.2.3", "major")
            '2.0.0'
            >>> VersionManager.bump("1.2.3", "minor")
            '1.3.0'
            >>> VersionManager.bump("1.2.3", "patch")
            '1.2.4'
        """
        v = parse(version)
        major, minor, patch = v.major, v.minor, v.micro

        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump_type: {bump_type}. Must be 'major', 'minor', or 'patch'")

    @staticmethod
    def compare(v1: str, v2: str) -> int:
        """Compare two version strings.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

        Example:
            >>> VersionManager.compare("1.2.3", "1.2.4")
            -1
            >>> VersionManager.compare("2.0.0", "1.9.9")
            1
            >>> VersionManager.compare("1.2.3", "1.2.3")
            0
        """
        ver1 = parse(v1)
        ver2 = parse(v2)

        if ver1 < ver2:
            return -1
        elif ver1 > ver2:
            return 1
        else:
            return 0

    @staticmethod
    def is_compatible(installed: str, required: str) -> bool:
        """Check if installed version satisfies required version.

        For simplicity, uses simple >= comparison.
        Could be extended to support semver ranges in the future.

        Args:
            installed: Installed version string
            required: Required version string

        Returns:
            True if installed >= required

        Example:
            >>> VersionManager.is_compatible("1.2.3", "1.2.0")
            True
            >>> VersionManager.is_compatible("1.2.3", "1.3.0")
            False
        """
        return parse(installed) >= parse(required)


def detect_bump_type(changes: list[str]) -> BumpType:
    """Infer bump type from list of changes.

    Simple heuristic:
    - If "breaking" or "BREAKING" appears -> major
    - If "feat" or "add" or "new" appears -> minor
    - Otherwise -> patch

    Args:
        changes: List of change descriptions

    Returns:
        Suggested bump type

    Example:
        >>> detect_bump_type(["add new feature", "fix bug"])
        'minor'
        >>> detect_bump_type(["fix typo"])
        'patch'
        >>> detect_bump_type(["BREAKING: remove old API"])
        'major'
    """
    changes_text = " ".join(changes).lower()

    # Check for breaking changes
    if "breaking" in changes_text:
        return "major"

    # Check for features
    if any(keyword in changes_text for keyword in ["feat", "add", "new"]):
        return "minor"

    # Default to patch
    return "patch"
