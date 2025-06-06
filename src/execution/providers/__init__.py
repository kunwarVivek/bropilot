"""
Provider-specific implementations for the LLM abstraction layer.

This package contains concrete implementations of the AbstractLLMProvider
for different LLM services, providing a unified interface while abstracting
vendor-specific details.
"""

from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

__all__ = [
    "OpenAIProvider",
    "GeminiProvider",
]

# Optional providers (may not be available)
try:
    from .anthropic_provider import AnthropicProvider
    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from .local_provider import LocalProvider
    __all__.append("LocalProvider")
except ImportError:
    pass
