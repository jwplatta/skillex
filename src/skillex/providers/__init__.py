"""Provider implementations for different AI agents.

Provides factory functions for creating and detecting providers.
"""

import os
from pathlib import Path
from typing import Optional

from .base import BaseProvider
from .claude import ClaudeProvider
from .codex import CodexProvider
from .gemini import GeminiProvider


# Registry of available providers
PROVIDERS = {
    "claude": ClaudeProvider,
    "codex": CodexProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str) -> Optional[BaseProvider]:
    """Get provider instance by name.

    Args:
        name: Provider name (claude, codex, gemini)

    Returns:
        Provider instance if found, None otherwise

    Example:
        >>> provider = get_provider("claude")
        >>> provider.get_skills_directory()
        PosixPath('/Users/user/.claude/skills')
    """
    provider_class = PROVIDERS.get(name.lower())
    if provider_class:
        return provider_class()
    return None


def detect_current_provider() -> Optional[str]:
    """Detect which provider context we're currently in.

    Checks in order:
    1. SKILLEX_PROVIDER environment variable
    2. Current working directory against known provider paths
    3. None if can't detect

    Returns:
        Provider name if detected, None otherwise

    Example:
        >>> os.environ["SKILLEX_PROVIDER"] = "claude"
        >>> detect_current_provider()
        'claude'
    """
    # Check environment variable
    if provider := os.getenv("SKILLEX_PROVIDER"):
        if provider.lower() in PROVIDERS:
            return provider.lower()

    # Check current working directory
    cwd = Path.cwd()

    for provider_name, provider_class in PROVIDERS.items():
        provider = provider_class()
        provider_dir = provider.get_skills_directory()

        try:
            # Check if cwd is within provider directory
            cwd.relative_to(provider_dir)
            return provider_name
        except ValueError:
            # Not relative to this provider directory
            continue

    return None


def list_providers() -> list[str]:
    """Get list of all available provider names.

    Returns:
        List of provider names

    Example:
        >>> list_providers()
        ['claude', 'codex', 'gemini']
    """
    return list(PROVIDERS.keys())


__all__ = [
    "BaseProvider",
    "ClaudeProvider",
    "CodexProvider",
    "GeminiProvider",
    "get_provider",
    "detect_current_provider",
    "list_providers",
]
