"""LLM adapter implementations."""

from cloudshift.infrastructure.llm.null_adapter import NullLLMAdapter
from cloudshift.infrastructure.llm.ollama_adapter import OllamaAdapter

__all__ = ["NullLLMAdapter", "OllamaAdapter"]
