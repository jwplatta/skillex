"""Gemini provider implementation."""

from pathlib import Path
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini agent.

    Skills directory: ~/.gemini/skills
    """

    def __init__(self):
        """Initialize Gemini provider."""
        super().__init__("gemini")

    def get_skills_directory(self) -> Path:
        """Return Gemini's skills directory.

        Returns:
            Path to ~/.gemini/skills
        """
        return self.resolve_skills_directory(".gemini")

    def get_provider_display_name(self) -> str:
        """Return the provider name used inside the bootstrap skill."""
        return "Gemini"
