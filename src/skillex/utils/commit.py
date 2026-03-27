"""Commit message generation utilities.

Implements the structured commit message format specified in the README:

Example commit message:
    feat(market-data): v0.2.0 | add realtime price endpoint

    CHANGES:
    - added websocket support
    - added symbol validation

    REASON:
    needed for live trading

    META:
    author=agent
    timestamp=2026-03-27T18:21:00Z
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

# Valid commit types from the spec
ALLOWED_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore"}


def generate_commit_message(
    type: str,
    skill: str,
    version: str,
    summary: str,
    changes: Optional[List[str]] = None,
    reason: Optional[str] = None,
    author: str = "agent",
    timestamp: Optional[str] = None,
) -> str:
    """Generate structured commit message for skill changes.

    Args:
        type: Commit type (feat, fix, refactor, docs, test, chore)
        skill: Skill name (lowercase, alphanumeric, hyphens only)
        version: Semantic version string (e.g., "0.2.0")
        summary: Brief summary (max 80 chars, will be truncated)
        changes: Optional list of changes to include
        reason: Optional reason/justification for changes
        author: Author identifier (default: "agent")
        timestamp: ISO timestamp (defaults to current time)

    Returns:
        Formatted commit message string

    Raises:
        ValueError: If type is invalid or skill name has invalid format

    Example:
        >>> msg = generate_commit_message(
        ...     type="feat",
        ...     skill="python-testing",
        ...     version="0.2.0",
        ...     summary="add coverage reporting",
        ...     changes=["added pytest-cov dependency", "updated test command"],
        ...     reason="needed for CI pipeline"
        ... )
        >>> print(msg)
        feat(python-testing): v0.2.0 | add coverage reporting

        CHANGES:
        - added pytest-cov dependency
        - updated test command

        REASON:
        needed for CI pipeline

        META:
        author=agent
        timestamp=2026-03-27T...
    """
    # Validate commit type
    if type not in ALLOWED_TYPES:
        raise ValueError(
            f"Invalid commit type '{type}'. Must be one of: {', '.join(sorted(ALLOWED_TYPES))}"
        )

    # Validate skill name format
    if not re.match(r"^[a-z0-9\-]+$", skill):
        raise ValueError(
            f"Invalid skill name '{skill}'. Must match pattern: ^[a-z0-9\\-]+$"
        )

    # Truncate summary if too long
    if len(summary) > 80:
        summary = summary[:80]

    # Use current timestamp if not provided
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    # Build commit message parts
    header = f"{type}({skill}): v{version} | {summary}"

    parts = [header]

    # Add CHANGES section if provided
    if changes:
        parts.append("\nCHANGES:")
        parts.extend([f"- {change}" for change in changes])

    # Add REASON section if provided
    if reason:
        parts.append("\nREASON:")
        parts.append(reason)

    # Always add META section
    parts.append("\nMETA:")
    parts.append(f"author={author}")
    parts.append(f"timestamp={timestamp}")

    return "\n".join(parts)


def validate_commit_type(type: str) -> bool:
    """Check if commit type is valid.

    Args:
        type: Commit type string to validate

    Returns:
        True if valid, False otherwise
    """
    return type in ALLOWED_TYPES


def validate_skill_name(name: str) -> bool:
    """Check if skill name matches required format.

    Skill names must be lowercase, alphanumeric, and may contain hyphens.

    Args:
        name: Skill name string to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_skill_name("python-testing")
        True
        >>> validate_skill_name("Python_Testing")
        False
        >>> validate_skill_name("my-skill-123")
        True
    """
    return bool(re.match(r"^[a-z0-9\-]+$", name))
