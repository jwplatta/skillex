"""Base provider class for AI agent providers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import textwrap
import shutil


class BaseProvider(ABC):
    """Base class for AI agent providers.

    Each provider (Claude, Codex, Gemini) has its own skills directory location.

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

    def get_bootstrap_skill_markdown(self) -> str:
        """Return a minimal neutral bootstrap skillex skill."""
        return textwrap.dedent(
            """
            ---
            name: skillex
            description: Manage shared skills with the skillex CLI
            ---

            # Skillex

            Use `skillex` to manage versioned skills from a shared repository.

            ## First Steps

            1. Configure the shared skills repo:

            ```bash
            skillex config set-remote <repo-url>
            ```

            2. Pull or push skills with an explicit agent:

            ```bash
            skillex pull <skill-name> --agent claude
            skillex push <skill-name> --agent codex --type docs --summary "describe the change"
            ```

            ## Notes

            - The shared source of truth lives in `~/.skillex`.
            - Installed copies live in agent-specific skills directories.
            - Use `skillex list` to inspect the shared repository contents.
            """
        ).strip() + "\n"

    def get_bootstrap_commands_markdown(self) -> str:
        """Return a compact bootstrap commands reference."""
        return textwrap.dedent(
            """
            # Skillex Commands

            ```bash
            skillex list
            skillex init claude
            skillex init codex
            skillex init gemini
            skillex pull <skill-name> --agent <claude|codex|gemini>
            skillex update <skill-name> --agent <claude|codex|gemini>
            skillex push <skill-name> --agent <claude|codex|gemini> --type <type> --summary "summary"
            skillex config set-remote <repo-url>
            ```
            """
        ).strip() + "\n"

    def materialize_skillex_skill(self, destination: Path) -> None:
        """Create a minimal bootstrap skillex skill into a destination directory."""

        if destination.exists():
            shutil.rmtree(destination)

        destination.mkdir(parents=True, exist_ok=True)
        references_dir = destination / "references"
        references_dir.mkdir(parents=True, exist_ok=True)
        (destination / "SKILL.md").write_text(self.get_bootstrap_skill_markdown())
        (references_dir / "commands.md").write_text(self.get_bootstrap_commands_markdown())

    def get_skillex_skill_content(self) -> str:
        """Return the bootstrap SKILL.md content."""
        return self.get_bootstrap_skill_markdown()

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
