"""
Execution adapters for external services.

This module provides adapters that bridge the execution layer with external
services like browser-use, LLM providers, and other automation tools.
"""

from .browser_use import BrowserUseAdapter
from .gemini import GeminiAdapter
from .openai import OpenAIAdapter
from .adapter_factory import AdapterFactory

__all__ = [
    "BrowserUseAdapter",
    "GeminiAdapter", 
    "OpenAIAdapter",
    "AdapterFactory"
]
