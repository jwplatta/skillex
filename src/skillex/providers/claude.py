"""Claude provider implementation."""

from pathlib import Path
from .base import BaseProvider


class ClaudeProvider(BaseProvider):
    """Provider for Claude Code agent.

    Skills directory: ~/.claude/skills
    """

    def __init__(self):
        """Initialize Claude provider."""
        super().__init__("claude")

    def get_skills_directory(self) -> Path:
        """Return Claude's skills directory.

        Returns:
            Path to ~/.claude/skills
        """
        return self.resolve_skills_directory(".claude")

    def get_provider_display_name(self) -> str:
        """Return the provider name used inside the bootstrap skill."""
        return "Claude"
