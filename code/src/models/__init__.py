"""
Package init for model adapters.
"""
from .base import ModelAdapter
from .gemini_adapter import GeminiAdapter
from .mock_adapter import MockAdapter
from .ollama_adapter import OllamaAdapter
from .openai_compatible_adapter import OpenAICompatibleAdapter
