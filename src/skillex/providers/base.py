"""Base provider class for AI agent providers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import shutil


class BaseProvider(ABC):
    """Base class for AI agent providers.

    Each provider (Claude, Codex, Gemini) has its own:
    - Skills directory location
    - Skillex skill content (provider-specific instructions)

    Example:
        >>> provider = ClaudeProvider()
        >>> skills_dir = provider.get_skills_directory()
        >>> provider.initialize()
    """

    def __init__(self, name: str):
        """Initialize base provider.

        Args:
            name: Provider name (e.g., "claude", "codex", "gemini")
        """
        self.name = name
        self.skills_dir: Optional[Path] = None

    def resolve_skills_directory(self, hidden_dir_name: str) -> Path:
        """Resolve the skills directory, preferring project-local test dirs."""
        cwd = Path.cwd().resolve()
        candidate_roots = [cwd, *cwd.parents]

        for root in candidate_roots:
            hidden_dir = root / hidden_dir_name
            if hidden_dir.exists():
                return hidden_dir / "skills"

        return Path.home() / hidden_dir_name / "skills"

    @abstractmethod
    def get_skills_directory(self) -> Path:
        """Return the skills directory for this provider.

        Returns:
            Path to provider's skills directory

        Example:
            >>> claude = ClaudeProvider()
            >>> claude.get_skills_directory()
            PosixPath('/Users/user/.claude/skills')
        """
        pass

    def get_provider_display_name(self) -> str:
        """Return a human-readable provider name."""
        return self.name

    def get_skill_template_directory(self) -> Path:
        """Return the source directory for the bootstrap skillex skill."""
        repo_root = Path(__file__).resolve().parents[3]
        repo_skill_dir = repo_root / "skill"
        if repo_skill_dir.exists():
            return repo_skill_dir

        packaged_skill_dir = Path(__file__).resolve().parents[1] / "templates" / "skillex-skill"
        if packaged_skill_dir.exists():
            return packaged_skill_dir

        raise FileNotFoundError("Could not find skillex bootstrap skill directory")

    def get_skill_template_context(self) -> dict[str, str]:
        """Return placeholder values used in the skillex bootstrap skill."""
        return {
            "provider": self.name,
            "provider_display": self.get_provider_display_name(),
            "skills_dir": str(self.get_skills_directory()),
        }

    def render_skill_template(self, content: str) -> str:
        """Render bootstrap skill file content for this provider."""
        rendered = content
        for key, value in self.get_skill_template_context().items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered

    def materialize_skillex_skill(self, destination: Path) -> None:
        """Copy the bootstrap skillex skill into a destination directory."""
        template_dir = self.get_skill_template_directory()

        if destination.exists():
            shutil.rmtree(destination)

        destination.mkdir(parents=True, exist_ok=True)

        for source_path in template_dir.rglob("*"):
            relative_path = source_path.relative_to(template_dir)
            target_path = destination / relative_path

            if source_path.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            rendered = self.render_skill_template(source_path.read_text())
            target_path.write_text(rendered)

    def get_skillex_skill_content(self) -> str:
        """Return the rendered SKILL.md content for this provider."""
        template_path = self.get_skill_template_directory() / "SKILL.md"
        return self.render_skill_template(template_path.read_text())

    def initialize(self) -> Path:
        """Initialize provider skills directory.

        Creates the skills directory if it doesn't exist.

        Returns:
            Path to initialized skills directory

        Example:
            >>> provider.initialize()
            PosixPath('/Users/user/.claude/skills')
        """
        skills_dir = self.get_skills_directory()
        skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir = skills_dir
        return skills_dir

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.name}')"
