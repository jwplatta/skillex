"""Antigravity provider implementation."""

from pathlib import Path

from .base import BaseProvider


class AntigravityProvider(BaseProvider):
    """Provider for Antigravity agent.

    Local skills directory: .agents/skills
    Global skills directory: ~/.gemini/antigravity-cli/skills
    """

    def __init__(self):
        """Initialize Antigravity provider."""
        super().__init__("antigravity")

    def get_skills_directory(self) -> Path:
        """Return Antigravity's skills directory.

        Returns:
            Path to .agents/skills when a workspace .agents directory exists,
            otherwise ~/.gemini/antigravity-cli/skills.
        """
        cwd = Path.cwd().resolve()

        for root in [cwd, *cwd.parents]:
            agents_dir = root / ".agents"
            if agents_dir.exists():
                return agents_dir / "skills"

        return Path.home() / ".gemini" / "antigravity-cli" / "skills"

    def get_provider_display_name(self) -> str:
        """Return the provider name used inside the bootstrap skill."""
        return "Antigravity"
