"""Codex provider implementation."""

from pathlib import Path
from .base import BaseProvider


class CodexProvider(BaseProvider):
    """Provider for OpenAI Codex agent.

    Skills directory: ~/.codex/skills
    """

    def __init__(self):
        """Initialize Codex provider."""
        super().__init__("codex")

    def get_skills_directory(self) -> Path:
        """Return Codex's skills directory.

        Returns:
            Path to ~/.codex/skills
        """
        return self.resolve_skills_directory(".codex")

    def get_provider_display_name(self) -> str:
        """Return the provider name used inside the bootstrap skill."""
        return "Codex"
